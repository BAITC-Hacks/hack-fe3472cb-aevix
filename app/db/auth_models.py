from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EmployeeAccount(Base):
    __tablename__ = "employee_accounts"

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"), primary_key=True)
    username: Mapped[str] = mapped_column(
        String(128), unique=True, index=True,
        default=lambda context: context.get_current_parameters()["employee_id"],
    )
    password_hash: Mapped[str] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "(role = 'hr' AND employee_id IS NULL) OR (role = 'employee' AND employee_id IS NOT NULL)",
            name="session_role_identity",
        ),
    )

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="hr")
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.employee_id"), nullable=True, index=True)
    credential_hash: Mapped[str] = mapped_column(String(64))
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


# Existing provisioning scripts and tests import this name. New sessions for both
# roles use the bound identity table; old unbound HR cookies are not reused.
HrSession = AuthSession
