import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.auth_models import HrSession
from app.db.database import get_db
from app.services.auth_service import COOKIE_NAME, check_login_limit, check_origin, clear_login_limit, create_session, find_session, require_hr, verify_password

router = APIRouter()


class HrLogin(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


def session_payload(session: HrSession | None) -> dict:
    if not session:
        return {"authenticated": False}
    return {"authenticated": True, "role": "hr", "username": session.username, "csrf_token": session.csrf_token, "expires_at": session.expires_at.isoformat() + "Z"}


@router.get("/session")
def get_session(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return session_payload(find_session(request, db))


@router.post("/hr/login")
def login(payload: HrLogin, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    check_origin(request)
    if not settings.hr_password_hash:
        raise HTTPException(503, "HR access has not been configured")
    peer = check_login_limit(request)
    password_ok = verify_password(payload.password, settings.hr_password_hash)
    if not password_ok or not hmac.compare_digest(payload.username.encode(), settings.hr_username.encode()):
        raise HTTPException(401, "Invalid username or password")
    clear_login_limit(peer)
    previous = find_session(request, db)
    if previous:
        db.delete(previous)
    token, session = create_session(db)
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.hr_cookie_secure or request.url.scheme == "https", samesite="strict", path="/api", max_age=max(1, settings.hr_session_hours) * 3600)
    response.headers["Cache-Control"] = "no-store"
    return session_payload(session)


@router.post("/logout")
def logout(response: Response, session: HrSession = Depends(require_hr), db: Session = Depends(get_db)) -> dict:
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api", httponly=True, samesite="strict", secure=settings.hr_cookie_secure)
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": False}
