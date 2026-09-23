import csv
from pathlib import Path
import stat

import pytest
from fastapi.testclient import TestClient

from app.db.auth_models import AuthSession, EmployeeAccount
from app.db.database import SessionLocal
from app.main import app
from app.services.auth_service import verify_password
from app.setup_employees import provision


def credentials(path: Path) -> dict:
    with path.open(newline="") as handle:
        return {row["employee_id"]: row for row in csv.DictReader(handle)}


def test_provisioning_is_private_idempotent_and_uses_individual_passwords(tmp_path):
    output = tmp_path / "private" / "access.csv"
    result = provision(["E0001", "E0002"], output=output)
    assert result["created"] == 2 and result["reset"] == 0
    rows = credentials(output)
    assert rows["E0001"]["password"] != rows["E0002"]["password"]
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    with SessionLocal() as db:
        for employee_id, row in rows.items():
            account = db.get(EmployeeAccount, employee_id)
            assert account.username == employee_id
            assert account.password_hash != row["password"]
            assert verify_password(row["password"], account.password_hash)
    before = output.read_bytes()
    assert provision(["E0001", "E0002"], output=output)["created"] == 0
    assert output.read_bytes() == before


def test_password_rotation_revokes_only_selected_employee_sessions(tmp_path):
    output = tmp_path / "access.csv"
    provision(["E0001", "E0002"], output=output)
    before = credentials(output)
    with TestClient(app) as employee, TestClient(app) as colleague:
        for client, employee_id in [(employee, "E0001"), (colleague, "E0002")]:
            result = client.post("/api/auth/login", json={"username": employee_id, "password": before[employee_id]["password"]})
            assert result.status_code == 200
        assert provision(["E0001"], rotate=True, output=output)["reset"] == 1
        after = credentials(output)
        assert before["E0001"]["password"] != after["E0001"]["password"]
        assert before["E0002"] == after["E0002"]
        assert employee.get("/api/auth/session").json() == {"authenticated": False}
        assert colleague.get("/api/auth/session").json()["employee_id"] == "E0002"
        assert employee.post("/api/auth/login", json={"username": "E0001", "password": before["E0001"]["password"]}).status_code == 401
        assert employee.post("/api/auth/login", json={"username": "E0001", "password": after["E0001"]["password"]}).status_code == 200
    with SessionLocal() as db:
        assert db.query(AuthSession).filter_by(employee_id="E0002").count() == 1


def test_unknown_employee_does_not_partially_provision(tmp_path):
    output = tmp_path / "access.csv"
    with pytest.raises(ValueError, match="Unknown employee"):
        provision(["E0001", "unknown"], output=output)
    assert not output.exists()
    with SessionLocal() as db:
        assert db.query(EmployeeAccount).count() == 0


def test_failed_export_preserves_recoverable_credentials_and_blocks_silent_retry(tmp_path, monkeypatch):
    def fail_replace(*args):
        raise OSError("Simulated disk failure")
    monkeypatch.setattr("app.setup_employees.os.replace", fail_replace)
    output = tmp_path / "access.csv"
    with pytest.raises(RuntimeError, match="private recovery file"):
        provision(["E0002"], output=output)
    recovery = next(tmp_path.glob(".access.csv.*.pending"))
    assert stat.S_IMODE(recovery.stat().st_mode) == 0o600
    row = credentials(recovery)["E0002"]
    with SessionLocal() as db:
        assert verify_password(row["password"], db.get(EmployeeAccount, "E0002").password_hash)
    with pytest.raises(RuntimeError, match="unfinished credentials export"):
        provision(["E0002"], output=output)
