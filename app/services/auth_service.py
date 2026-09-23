from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.auth_models import AuthSession, EmployeeAccount
from app.db.database import get_db
from app.db.models import Employee

COOKIE_NAME = "cq_hr_session"
_failures: dict[str, list[float]] = {}
_lock = threading.Lock()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or not 100_000 <= int(iterations) <= 2_000_000:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    same_origin = f"{request.url.scheme}://{request.url.netloc}"
    if origin and origin.rstrip("/") not in [same_origin, *settings.cors_origins]:
        raise HTTPException(403, "Untrusted request origin")


def check_login_limit(request: Request, username: str) -> str:
    # Do not trust client-supplied forwarding headers for the rate-limit key.
    peer = request.client.host if request.client else "unknown"
    key = f"identity:{len(peer)}:{peer}{username}"
    peer_key = f"peer:{peer}"
    now = time.monotonic()
    with _lock:
        for stale in [identity for identity, attempts in _failures.items() if not attempts or attempts[-1] <= now - 300]:
            del _failures[stale]
        attempts = [at for at in _failures.get(key, []) if at > now - 300]
        burst = [at for at in _failures.get(peer_key, []) if at > now - 60]
        if len(attempts) >= 5 or len(burst) >= 300 or (key not in _failures and len(_failures) >= 10_000):
            raise HTTPException(429, "Too many login attempts. Try again in 5 minutes.", headers={"Retry-After": "300"})
        # Count attempts before verification so concurrent requests cannot bypass the limit.
        _failures[key] = [*attempts, now]
        _failures[peer_key] = [*burst, now]
    return key


def clear_login_limit(key: str) -> None:
    with _lock:
        _failures.pop(key, None)


def _credential_hash(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()


def find_session(request: Request, db: Session) -> AuthSession | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 256:
        return None
    session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires_at <= datetime.utcnow():
        return None
    if session.role == "hr":
        if session.employee_id is not None or session.username != settings.hr_username or not settings.hr_password_hash:
            return None
        password_hash = settings.hr_password_hash
    elif session.role == "employee":
        account = db.get(EmployeeAccount, session.employee_id) if session.employee_id else None
        if (
            account is None or not account.active or not account.password_hash
            or account.username != session.username or db.get(Employee, session.employee_id) is None
        ):
            return None
        password_hash = account.password_hash
    else:
        return None
    if not hmac.compare_digest(session.credential_hash, _credential_hash(password_hash)):
        return None
    return session


def require_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    session = find_session(request, db)
    if not session:
        raise HTTPException(401, "Sign-in required")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", "").encode(), session.csrf_token.encode()):
            raise HTTPException(403, "Invalid CSRF token")
    return session


def require_hr(session: AuthSession = Depends(require_session)) -> AuthSession:
    if session.role != "hr":
        raise HTTPException(403, "HR access required")
    return session


def assert_employee_access(session: AuthSession, employee_id: str, allow_hr: bool = True) -> None:
    if session.role == "hr":
        if allow_hr:
            return
        raise HTTPException(403, "HR employee preview is read-only")
    if session.role != "employee" or session.employee_id != employee_id:
        raise HTTPException(403, "You can only access your own employee profile")


def require_employee_access(employee_id: str, session: AuthSession = Depends(require_session)) -> AuthSession:
    assert_employee_access(session, employee_id)
    return session


def require_employee_actor(employee_id: str, session: AuthSession = Depends(require_session)) -> AuthSession:
    assert_employee_access(session, employee_id, allow_hr=False)
    return session


def create_session(
    db: Session, *, role: str = "hr", employee_id: str | None = None, username: str | None = None,
) -> tuple[str, AuthSession]:
    if role == "hr":
        if employee_id is not None or not settings.hr_password_hash:
            raise HTTPException(503, "HR access has not been configured")
        if username is not None and username != settings.hr_username:
            raise HTTPException(401, "Invalid account")
        username = settings.hr_username
        password_hash = settings.hr_password_hash
    elif role == "employee":
        account = db.get(EmployeeAccount, employee_id) if employee_id else None
        if (
            account is None or not account.active or not account.password_hash
            or db.get(Employee, employee_id) is None or (username is not None and account.username != username)
        ):
            raise HTTPException(401, "Invalid account")
        username = account.username
        password_hash = account.password_hash
    else:
        raise HTTPException(401, "Invalid account")
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        username=username, role=role, employee_id=employee_id,
        credential_hash=_credential_hash(password_hash),
        csrf_token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(hours=max(1, settings.hr_session_hours)),
    )
    db.query(AuthSession).filter(AuthSession.expires_at <= datetime.utcnow()).delete()
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session
