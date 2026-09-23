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


class QuestProgress(Base):
    __tablename__ = "quest_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False)
    status = Column(String, nullable=False, default="recommended")
    mode = Column(String, nullable=False, default="solo")
    started_at = Column(Date, nullable=True)
    completed_at = Column(Date, nullable=True)


class QuestStepProgress(Base):
    __tablename__ = "quest_step_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    completed_at = Column(Date, nullable=True)


class QuestPlan(Base):
    __tablename__ = "quest_plans"

    employee_id = Column(String, ForeignKey("employees.employee_id"), primary_key=True)
    event_id = Column(String, ForeignKey("events.event_id"), primary_key=True)
    provider = Column(String, nullable=False, default="template")
    language = Column(String, nullable=False, default="ru")
    task = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)
    created_at = Column(Date, nullable=False, default=date.today)


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    creator_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    max_members = Column(Integer, nullable=False, default=5)
    status = Column(String, nullable=False, default="active")
    completed_team_quests = Column(Integer, nullable=False, default=0)
    current_event_id = Column(String, ForeignKey("events.event_id"), nullable=True)
    quest_started_at = Column(Date, nullable=True)


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, ForeignKey("teams.team_id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)


class ESGGoal(Base):
    __tablename__ = "esg_goals"

    goal_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_coins = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="pending_hr_review")


class ESGContribution(Base):
    __tablename__ = "esg_contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(String, ForeignKey("esg_goals.goal_id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    coins = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending_hr_review")
    created_at = Column(Date, nullable=False)


class PairInvitation(Base):
    __tablename__ = "pair_invitations"

    invitation_id = Column(String, primary_key=True, index=True)
    inviter_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    format = Column(String, nullable=False)
    display_mode = Column(String, nullable=False, default="name")
    display_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(Date, nullable=False)


class PairSpace(Base):
    __tablename__ = "pair_spaces"

    pair_id = Column(String, primary_key=True, index=True)
    invitation_id = Column(String, ForeignKey("pair_invitations.invitation_id"), nullable=False)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False)
    inviter_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    partner_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(Date, nullable=False)
