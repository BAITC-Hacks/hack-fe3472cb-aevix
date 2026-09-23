"""Keep every backend test isolated from the developer's working database."""
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import database
from app.core.config import settings
from app.services import hr_service  # Load its SessionLocal before patching aliases.
from app.services.import_service import seed_demo_data
from app.services.auth_service import hash_password, _failures
from app.db.auth_models import EmployeeAccount
from app.db.models import Employee

TEST_HR_PASSWORD = "test-hr-credentials-only"
TEST_HR_HASH = hash_password(TEST_HR_PASSWORD)


@pytest.fixture
def employee_sign_in():
    """Provision an isolated employee account and perform a real password login."""
    def sign_in(client, employee_id="E0002"):
        with database.SessionLocal() as db:
            assert db.get(Employee, employee_id) is not None
            account = db.get(EmployeeAccount, employee_id)
            if not account:
                db.add(EmployeeAccount(employee_id=employee_id, username=employee_id, password_hash=TEST_HR_HASH, active=True))
                db.commit()
        _failures.clear()
        response = client.post("/api/auth/login", json={"username": employee_id, "password": TEST_HR_PASSWORD})
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return client
    return sign_in


@pytest.fixture
def hr_sign_in(monkeypatch):
    monkeypatch.setattr(settings, "hr_username", "hr")
    monkeypatch.setattr(settings, "hr_password_hash", TEST_HR_HASH)
    _failures.clear()

    def sign_in(client):
        response = client.post("/api/auth/hr/login", json={"username": "hr", "password": TEST_HR_PASSWORD})
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return client

    return sign_in


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "hr_username", "hr")
    monkeypatch.setattr(settings, "hr_password_hash", TEST_HR_HASH)
    _failures.clear()
    engine = create_engine(f"sqlite:///{tmp_path / 'workspace.sqlite'}")
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(database, "engine", engine)
    for name, module in list(sys.modules.items()):
        if (name.startswith("app.") or name.startswith("test_")) and hasattr(module, "SessionLocal"):
            monkeypatch.setattr(module, "SessionLocal", factory)
    database.init_db()
    seed_demo_data()
    yield
    engine.dispose()
