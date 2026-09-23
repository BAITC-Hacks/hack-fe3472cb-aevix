import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.auth_models import AuthSession, EmployeeAccount
from app.db.database import get_db
from app.db.models import Employee
from app.services.auth_service import COOKIE_NAME, check_login_limit, check_origin, clear_login_limit, create_session, find_session, require_session, verify_password

router = APIRouter()


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("username")
    @classmethod
    def nonempty_username(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("username is required")
        return value.strip()


HrLogin = LoginPayload
_DUMMY_PASSWORD_HASH = "pbkdf2_sha256$600000$00000000000000000000000000000000$" + "0" * 64


def session_payload(session: AuthSession | None) -> dict:
    if not session:
        return {"authenticated": False}
    return {
        "authenticated": True, "role": session.role, "username": session.username,
        "employee_id": session.employee_id, "csrf_token": session.csrf_token,
        "expires_at": session.expires_at.isoformat() + "Z",
    }


@router.get("/session")
def get_session(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return session_payload(find_session(request, db))


def _login(payload: LoginPayload, request: Request, response: Response, db: Session, hr_only: bool = False) -> dict:
    check_origin(request)
    if hr_only and not settings.hr_password_hash:
        raise HTTPException(503, "HR access has not been configured")
    peer = check_login_limit(request)
    employee_id = None
    is_hr_username = hmac.compare_digest(payload.username.encode(), settings.hr_username.encode())
    if hr_only or is_hr_username:
        password_ok = verify_password(payload.password, settings.hr_password_hash or _DUMMY_PASSWORD_HASH)
        valid = password_ok and is_hr_username and bool(settings.hr_password_hash)
        role = "hr"
    else:
        account = db.query(EmployeeAccount).filter_by(username=payload.username).first()
        password_ok = verify_password(payload.password, account.password_hash if account else _DUMMY_PASSWORD_HASH)
        valid = bool(account and account.active and password_ok and db.get(Employee, account.employee_id))
        employee_id = account.employee_id if account else None
        role = "employee"
    if not valid:
        raise HTTPException(401, "Invalid username or password")
    clear_login_limit(peer)
    previous = find_session(request, db)
    if previous:
        db.delete(previous)
    token, session = create_session(db, role=role, employee_id=employee_id, username=payload.username)
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.hr_cookie_secure or request.url.scheme == "https", samesite="strict", path="/api", max_age=max(1, settings.hr_session_hours) * 3600)
    response.headers["Cache-Control"] = "no-store"
    return session_payload(session)


@router.post("/login")
def login(payload: LoginPayload, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    return _login(payload, request, response, db)


@router.post("/hr/login")
def hr_login(payload: LoginPayload, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    return _login(payload, request, response, db, hr_only=True)


@router.post("/logout")
def logout(response: Response, session: AuthSession = Depends(require_session), db: Session = Depends(get_db)) -> dict:
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api", httponly=True, samesite="strict", secure=settings.hr_cookie_secure)
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": False}
