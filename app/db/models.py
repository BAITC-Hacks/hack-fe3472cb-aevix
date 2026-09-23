from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    role = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    manager_id = Column(String, nullable=True)
    hire_date = Column(Date, nullable=True)
    tenure_months = Column(Integer, nullable=True)
    work_format = Column(String, nullable=True)
    preferred_language = Column(String, nullable=True)
    career_goal = Column(JSON, nullable=True)
    skills = Column(JSON, default=dict)
    last_review_date = Column(Date, nullable=True)

    history = relationship("ActivityHistory", back_populates="employee")


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)


class RoleProfile(Base):
    __tablename__ = "role_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    required_skills = Column(JSON, default=dict)
    critical_skills = Column(JSON, default=list)


class Event(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=True)
    format = Column(String, nullable=True)
    duration_hours = Column(Integer, nullable=True)
    mandatory = Column(Boolean, default=False)
    target_roles = Column(JSON, default=list)
    target_grades = Column(JSON, default=list)
    develops_skills = Column(JSON, default=list)
    prerequisites = Column(JSON, default=dict)
    upcoming_sessions = Column(JSON, default=list)


class ActivityHistory(Base):
    __tablename__ = "activity_history"

    record_id = Column(String, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    event_id = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String, nullable=True)
    completion_pct = Column(Integer, nullable=True)
    score = Column(Integer, nullable=True)
    feedback_rating = Column(Integer, nullable=True)
    assigned_by = Column(String, nullable=True)

    employee = relationship("Employee", back_populates="history")


class Wallet(Base):
    __tablename__ = "wallets"

    employee_id = Column(String, ForeignKey("employees.employee_id"), primary_key=True)
    balance = Column(Integer, nullable=False, default=0)


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    event_id = Column(String, nullable=True)
    amount = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(Date, nullable=False)
