from fastapi.testclient import TestClient

from app.main import app


def test_failed_hr_login_does_not_block_staff_or_reset_when_staff_signs_in(employee_sign_in):
    with TestClient(app) as client:
        employee_sign_in(client, "E0002")
        for _ in range(5):
            assert client.post("/api/auth/login", json={"username": "hr", "password": "wrong-password"}).status_code == 401
        # Coworkers behind the same proxy can still sign in to their own accounts.
        assert client.post("/api/auth/login", json={"username": "E0002", "password": "test-hr-credentials-only"}).status_code == 200
        # A successful employee login cannot clear the limiter for HR credentials.
        assert client.post("/api/auth/login", json={"username": "hr", "password": "test-hr-credentials-only"}).status_code == 429
