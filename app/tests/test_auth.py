"""Real HTTP checks for HR access; isolated test credentials and no auth overrides."""
from datetime import datetime, timedelta
import hashlib
import json
import time

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.db.auth_models import HrSession
from app.db.database import SessionLocal
from app.db.models import Employee
from app.main import app
from app.services import auth_service


TEST_PASSWORD = "Only-for-isolated-auth-tests!"
TEST_HASH = auth_service.hash_password(TEST_PASSWORD)
HR_PATHS = [f"/api/hr/{name}" for name in (
    "dashboard", "skill-gaps", "inactive-employees", "events-effectiveness", "esg-engagement",
)]
MUTATION_PATHS = [f"/api/import/{name}" for name in (
    "dataset", "employees", "events", "skills", "history", "check-profiles", "check-history", "jury-dataset",
)] + ["/api/employees/register"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "hr_username", "test-hr")
    monkeypatch.setattr(settings, "hr_password_hash", TEST_HASH)
    monkeypatch.setattr(settings, "hr_cookie_secure", False)
    monkeypatch.setattr(settings, "hr_session_hours", 1)
    monkeypatch.setattr(settings, "allowed_origins", "http://localhost:5173")
    with auth_service._lock:
        auth_service._failures.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    with auth_service._lock:
        auth_service._failures.clear()


def login(client):
    response = client.post("/api/auth/hr/login", json={"username": "test-hr", "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return response


def mutation(client, path, headers=None):
    options = {"headers": headers} if headers is not None else {}
    employee = {"employee_id": "AUTH_IMPORT", "full_name": "Imported Test Employee"}
    if path == "/api/employees/register":
        return client.post(path, json=employee, **options)
    if path.endswith("/dataset"):
        return client.post(path, **options)
    if path.endswith("/jury-dataset"):
        return client.post(path, files={"employees": ("employees.json", json.dumps({"employees": [employee]}))}, **options)
    if path.endswith(("/history", "/check-history")):
        data = "record_id,employee_id,event_id,status\nAUTH_HISTORY,E0002,EV_005,registered\n"
        return client.post(path, files={"file": ("history.csv", data)}, **options)
    key = "employees" if path.endswith(("/employees", "/check-profiles")) else path.rsplit("/", 1)[1]
    records = {
        "employees": [employee], "events": [{"event_id": "AUTH_EVENT", "title": "Test event"}],
        "skills": [{"skill_id": "AUTH_SKILL", "name": "Test skill", "type": "hard"}],
    }
    return client.post(path, files={"file": (f"{key}.json", json.dumps({key: records[key]}))}, **options)


@pytest.mark.parametrize("path", HR_PATHS)
def test_all_hr_routes_reject_unauthenticated_and_forged_roles(client, path):
    assert client.get(path).status_code == 401
    client.cookies.set(auth_service.COOKIE_NAME, "forged-hr-session", path="/api")
    response = client.get(path, headers={"X-Role": "hr", "X-User-Role": "hr", "Authorization": "Bearer hr"})
    assert response.status_code == 401


@pytest.mark.parametrize("path", MUTATION_PATHS)
def test_import_and_registration_require_hr_session_before_mutating(client, path):
    assert mutation(client, path).status_code == 401
    client.cookies.set(auth_service.COOKIE_NAME, "forged-hr-session", path="/api")
    assert mutation(client, path, headers={"X-Role": "hr", "X-CSRF-Token": "forged"}).status_code == 401
    with SessionLocal() as db:
        assert db.get(Employee, "AUTH_IMPORT") is None


def test_login_cookie_authenticates_all_hr_routes_and_stores_only_token_hash(client):
    assert client.get("/api/auth/session").json() == {"authenticated": False}
    response = login(client)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    assert response.headers["cache-control"] == "no-store"
    token = client.cookies.get(auth_service.COOKIE_NAME)
    assert token and token not in response.text
    with SessionLocal() as db:
        session = db.query(HrSession).one()
        assert session.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert session.token_hash != token
    session_response = client.get("/api/auth/session")
    assert session_response.json()["authenticated"] is True
    assert session_response.json()["role"] == "hr"
    assert session_response.headers["cache-control"] == "no-store"
    for path in HR_PATHS:
        assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", MUTATION_PATHS)
def test_every_protected_mutation_requires_csrf_even_with_valid_session(client, path):
    login(client)
    assert mutation(client, path).status_code == 403
    assert mutation(client, path, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    with SessionLocal() as db:
        assert db.get(Employee, "AUTH_IMPORT") is None


def test_valid_csrf_allows_registration_and_upload(client):
    csrf = login(client).json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf, "Origin": "http://testserver"}
    assert mutation(client, "/api/import/employees", headers=headers).status_code == 200
    response = client.post("/api/employees/register", json={
        "employee_id": "AUTH_REGISTER", "full_name": "Registered Test Employee",
    }, headers=headers)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        assert db.get(Employee, "AUTH_IMPORT") is not None
        assert db.get(Employee, "AUTH_REGISTER") is not None


def test_wrong_credentials_are_generic_and_login_attempts_are_limited(client):
    for index in range(5):
        response = client.post("/api/auth/hr/login", json={
            "username": "test-hr" if index % 2 else "unknown", "password": "wrong-password",
        }, headers={"X-Forwarded-For": f"192.0.2.{index}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"
    blocked = client.post("/api/auth/hr/login", json={"username": "test-hr", "password": TEST_PASSWORD})
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "300"
    assert auth_service.COOKIE_NAME not in client.cookies
    with auth_service._lock:
        auth_service._failures["testclient"] = [time.monotonic() - 301]
    assert login(client).json()["authenticated"] is True


def test_expired_session_is_rejected_on_reads_and_mutations(client):
    csrf = login(client).json()["csrf_token"]
    with SessionLocal() as db:
        session = db.query(HrSession).one()
        session.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/auth/session").json() == {"authenticated": False}
    assert client.get(HR_PATHS[0]).status_code == 401
    assert mutation(client, "/api/import/employees", headers={"X-CSRF-Token": csrf}).status_code == 401


def test_logout_requires_csrf_and_revokes_cookie_replay(client):
    csrf = login(client).json()["csrf_token"]
    old_token = client.cookies.get(auth_service.COOKIE_NAME)
    assert client.post("/api/auth/logout").status_code == 403
    assert client.get("/api/auth/session").json()["authenticated"] is True
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200 and response.json() == {"authenticated": False}
    assert response.headers["cache-control"] == "no-store"
    assert auth_service.COOKIE_NAME not in client.cookies
    client.cookies.set(auth_service.COOKIE_NAME, old_token, path="/api")
    assert client.get(HR_PATHS[0]).status_code == 401
    with SessionLocal() as db:
        assert db.query(HrSession).count() == 0


def test_repeated_login_rotates_and_revokes_previous_session(client):
    login(client)
    old_token = client.cookies.get(auth_service.COOKIE_NAME)
    login(client)
    assert client.cookies.get(auth_service.COOKIE_NAME) != old_token
    with SessionLocal() as db:
        assert db.query(HrSession).count() == 1
    with TestClient(app, raise_server_exceptions=False) as stale_client:
        stale_client.cookies.set(auth_service.COOKIE_NAME, old_token, path="/api")
        assert stale_client.get(HR_PATHS[0]).status_code == 401


def test_untrusted_origin_blocks_login_and_authenticated_mutations(client):
    response = client.post("/api/auth/hr/login", json={"username": "test-hr", "password": TEST_PASSWORD}, headers={"Origin": "https://attacker.example"})
    assert response.status_code == 403
    csrf = login(client).json()["csrf_token"]
    assert mutation(client, "/api/import/employees", headers={
        "X-CSRF-Token": csrf, "Origin": "https://attacker.example",
    }).status_code == 403
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf, "Origin": "null"}).status_code == 403
    assert client.get("/api/auth/session").json()["authenticated"] is True


def test_non_ascii_csrf_header_is_rejected_without_server_error(client):
    login(client)
    response = client.post("/api/auth/logout", headers=[(b"X-CSRF-Token", b"\xff")])
    assert response.status_code == 403, response.text


def test_https_login_sets_secure_cookie(client):
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as https_client:
        response = login(https_client)
        assert "secure" in response.headers["set-cookie"].lower()
        assert https_client.get(HR_PATHS[0]).status_code == 200


def test_unconfigured_hr_access_stays_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "hr_password_hash", None)
    response = client.post("/api/auth/hr/login", json={"username": "test-hr", "password": TEST_PASSWORD})
    assert response.status_code == 503
    assert client.get(HR_PATHS[0]).status_code == 401


@pytest.mark.parametrize("encoded", ["", "plain-password", "pbkdf2_sha256$1$00$anything", "unknown$600000$00$anything", "pbkdf2_sha256$600000$not-hex$anything"])
def test_malformed_password_configuration_fails_closed(encoded):
    assert auth_service.verify_password(TEST_PASSWORD, encoded) is False
