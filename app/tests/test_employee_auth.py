"""Identity is server-bound: employees access themselves and HR previews are read-only."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.db.auth_models import AuthSession, EmployeeAccount
from app.db.database import SessionLocal
from app.db.models import CoinTransaction, QuestPlan, QuestProgress
from app.main import app
from app.services import auth_service, quest_service


EMPLOYEE_PASSWORD = "Isolated-employee-password-123!"
EMPLOYEE_HASH = auth_service.hash_password(EMPLOYEE_PASSWORD)


def provision(employee_id="E0002"):
    with SessionLocal() as db:
        db.add(EmployeeAccount(employee_id=employee_id, password_hash=EMPLOYEE_HASH))
        db.commit()


@pytest.fixture
def employee_client():
    provision()
    with auth_service._lock:
        auth_service._failures.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/login", json={"username": "E0002", "password": EMPLOYEE_PASSWORD})
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        yield client
    with auth_service._lock:
        auth_service._failures.clear()


def employee_paths(employee_id):
    return [
        f"/api/employees/{employee_id}", f"/api/employees/{employee_id}/profile",
        f"/api/employees/{employee_id}/trajectory", f"/api/employees/{employee_id}/recommendations",
        f"/api/recommendations/{employee_id}", f"/api/game/{employee_id}/map",
        f"/api/game/{employee_id}/progress", f"/api/game/{employee_id}/quests",
        f"/api/wallet/{employee_id}", f"/api/employees/{employee_id}/quests/EV_005/steps",
    ]


def test_employee_identity_is_bound_in_server_session_and_list(employee_client):
    session = employee_client.get("/api/auth/session").json()
    assert session["authenticated"]
    assert session["role"] == "employee"
    assert session["username"] == session["employee_id"] == "E0002"
    assert [row["employee_id"] for row in employee_client.get("/api/employees").json()] == ["E0002"]
    with SessionLocal() as db:
        account = db.get(EmployeeAccount, "E0002")
        assert account.username == "E0002" and account.active
        row = db.query(AuthSession).one()
        assert row.role == "employee" and row.employee_id == "E0002"
        assert row.credential_hash and EMPLOYEE_PASSWORD not in row.credential_hash


def test_employee_reads_own_private_routes_but_cannot_read_others(employee_client):
    for path in employee_paths("E0002"):
        response = employee_client.get(path)
        assert response.status_code == 200, (path, response.text)
        assert response.headers["Cache-Control"] == "no-store"
    for path in employee_paths("E0001"):
        response = employee_client.get(path, headers={"X-Employee-ID": "E0001", "X-Role": "hr"})
        assert response.status_code == 403, (path, response.text)
    assert employee_client.get("/api/hr/dashboard").status_code == 403
    assert employee_client.post("/api/employees/register", json={"employee_id": "FAKE", "full_name": "Fake"}).status_code == 403
    assert employee_client.post("/api/import/dataset").status_code == 403


def test_directory_and_catalog_share_no_private_profile_fields(employee_client):
    directory = employee_client.get("/api/employees/directory")
    assert directory.status_code == 200
    assert any(row["employee_id"] == "E0001" for row in directory.json())
    assert all(set(row) == {"employee_id", "full_name", "role", "department"} for row in directory.json())
    catalog = employee_client.get("/api/employees/catalog")
    assert catalog.status_code == 200
    assert set(catalog.json()) == {"skills", "events", "role_profiles"}


def test_private_routes_require_session_and_ignore_forged_identity_headers():
    with TestClient(app, raise_server_exceptions=False) as client:
        for path in ["/api/employees", "/api/employees/catalog", "/api/employees/directory", *employee_paths("E0002")]:
            assert client.get(path, headers={"X-Role": "hr", "X-Employee-ID": "E0002"}).status_code == 401
        client.cookies.set(auth_service.COOKIE_NAME, "fake-bound-session", path="/api")
        assert client.get("/api/employees/E0002/profile").status_code == 401


def test_employee_mutations_require_csrf_and_matching_identity(employee_client):
    own = "/api/employees/E0002/quests/EV_005"
    other = "/api/employees/E0001/quests/EV_005"
    csrf = employee_client.headers.pop("X-CSRF-Token")
    assert employee_client.post(own + "/select").status_code == 403
    assert employee_client.post(own + "/complete").status_code == 403
    assert employee_client.post(own + "/steps/1/complete").status_code == 403
    employee_client.headers["X-CSRF-Token"] = csrf
    for action in ("select", "complete", "steps/1/complete"):
        assert employee_client.post(other + "/" + action, json={"employee_id": "E0002"}).status_code == 403
    assert employee_client.post(own + "/select", headers={"Origin": "https://attacker.example"}).status_code == 403
    assert employee_client.post(own + "/select").status_code == 200
    assert employee_client.get(own + "/steps").status_code == 200
    assert employee_client.post(own + "/steps/1/complete").status_code == 200
    with SessionLocal() as db:
        assert db.query(QuestProgress).filter_by(employee_id="E0001", event_id="EV_005").count() == 0
        assert db.query(CoinTransaction).count() == 0


def test_hr_can_preview_profiles_but_cannot_change_employee_work(hr_sign_in, monkeypatch):
    def unexpected_generation(*args, **kwargs):
        pytest.fail("HR preview must never generate or persist an employee plan")

    monkeypatch.setattr(quest_service, "generate_quest_steps", unexpected_generation)
    with TestClient(app, raise_server_exceptions=False) as client:
        hr_sign_in(client)
        assert client.get("/api/auth/session").json()["employee_id"] is None
        assert len(client.get("/api/employees").json()) > 1
        for employee_id in ("E0001", "E0002"):
            assert client.get(f"/api/employees/{employee_id}/profile").status_code == 200
        base = "/api/employees/E0002/quests/EV_005"
        response = client.get(base + "/steps", params={"read_only": "false"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Quest plan not started"
        for action in ("select", "complete", "steps/1/complete"):
            assert client.post(base + "/" + action).status_code == 403
    with SessionLocal() as db:
        assert db.query(QuestPlan).count() == 0
        assert db.query(QuestProgress).count() == 0
        assert db.query(CoinTransaction).count() == 0


def test_hr_reads_existing_plan_without_changing_it(employee_client, hr_sign_in):
    path = "/api/employees/E0002/quests/EV_005/steps"
    plan = employee_client.get(path).json()
    with TestClient(app, raise_server_exceptions=False) as hr_client:
        hr_sign_in(hr_client)
        assert hr_client.get(path).json() == plan
    with SessionLocal() as db:
        assert db.query(QuestPlan).count() == 1


@pytest.mark.parametrize("change", ["deactivate", "password", "username", "delete"])
def test_account_changes_revoke_existing_employee_session(employee_client, change):
    with SessionLocal() as db:
        account = db.get(EmployeeAccount, "E0002")
        if change == "deactivate":
            account.active = False
        elif change == "password":
            account.password_hash = auth_service.hash_password("A-different-test-password!")
        elif change == "username":
            account.username = "renamed-account"
        else:
            db.delete(account)
        db.commit()
    assert employee_client.get("/api/auth/session").json() == {"authenticated": False}
    assert employee_client.get("/api/employees/E0002/profile").status_code == 401
    assert employee_client.post("/api/employees/E0002/quests/EV_005/select").status_code == 401


def test_employee_login_works_when_hr_credentials_are_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "hr_password_hash", None)
    provision()
    with auth_service._lock:
        auth_service._failures.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/login", json={"username": "E0002", "password": EMPLOYEE_PASSWORD})
        assert response.status_code == 200
        assert response.json()["role"] == "employee"


def test_client_cannot_choose_role_or_bound_employee_id_in_login(employee_client):
    for fields in ({"role": "hr"}, {"employee_id": "E0001"}):
        response = employee_client.post("/api/auth/login", json={
            "username": "E0002", "password": EMPLOYEE_PASSWORD, **fields,
        })
        assert response.status_code == 422
    assert employee_client.get("/api/auth/session").json()["employee_id"] == "E0002"


def test_hr_alias_cannot_authenticate_employee_credentials(employee_client, hr_sign_in):
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/hr/login", json={"username": "E0002", "password": EMPLOYEE_PASSWORD})
        assert response.status_code == 401
        assert client.get("/api/auth/session").json() == {"authenticated": False}


def test_employee_logout_revokes_cookie_replay(employee_client):
    old_token = employee_client.cookies.get(auth_service.COOKIE_NAME)
    assert employee_client.post("/api/auth/logout").status_code == 200
    assert employee_client.get("/api/auth/session").json() == {"authenticated": False}
    employee_client.cookies.set(auth_service.COOKIE_NAME, old_token, path="/api")
    assert employee_client.get("/api/employees/E0002/profile").status_code == 401


def test_expired_employee_session_cannot_read_or_mutate(employee_client):
    with SessionLocal() as db:
        session = db.query(AuthSession).one()
        session.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert employee_client.get("/api/employees/E0002/profile").status_code == 401
    assert employee_client.post("/api/employees/E0002/quests/EV_005/select").status_code == 401
