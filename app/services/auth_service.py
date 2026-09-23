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
from app.db.auth_models import HrSession
from app.db.database import get_db

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


def check_login_limit(request: Request) -> str:
    # Do not trust client-supplied forwarding headers for the rate-limit key.
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        for stale in [peer for peer, attempts in _failures.items() if not attempts or attempts[-1] <= now - 300]:
            del _failures[stale]
        attempts = [at for at in _failures.get(key, []) if at > now - 300]
        if len(attempts) >= 5 or (key not in _failures and len(_failures) >= 10_000):
            raise HTTPException(429, "Too many login attempts. Try again in 5 minutes.", headers={"Retry-After": "300"})
        # Count attempts before verification so concurrent requests cannot bypass the limit.
        _failures[key] = [*attempts, now]
    return key


def clear_login_limit(key: str) -> None:
    with _lock:
        _failures.pop(key, None)


def find_session(request: Request, db: Session) -> HrSession | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 256:
        return None
    session = db.get(HrSession, hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires_at <= datetime.utcnow() or session.username != settings.hr_username or not settings.hr_password_hash:
        return None
    return session


def require_hr(request: Request, db: Session = Depends(get_db)) -> HrSession:
    session = find_session(request, db)
    if not session:
        raise HTTPException(401, "HR sign-in required")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf_token):
            raise HTTPException(403, "Invalid CSRF token")
    return session


def create_session(db: Session) -> tuple[str, HrSession]:
    token = secrets.token_urlsafe(32)
    session = HrSession(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        username=settings.hr_username,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(hours=max(1, settings.hr_session_hours)),
    )
    db.query(HrSession).filter(HrSession.expires_at <= datetime.utcnow()).delete()
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session
