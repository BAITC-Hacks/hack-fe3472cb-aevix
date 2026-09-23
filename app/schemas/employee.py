from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class CareerGoal(BaseModel):
    target_role: str | None = None
    target_grade: str | None = None


class EmployeeBase(BaseModel):
    employee_id: str
    full_name: str
    department: str | None = None
    role: str | None = None
    grade: str | None = None
    manager_id: str | None = None
    hire_date: date | None = None
    tenure_months: int | None = None
    work_format: str | None = None
    preferred_language: str | None = None
    career_goal: CareerGoal | None = None
    skills: dict[str, int] = Field(default_factory=dict)
    last_review_date: date | None = None


class EmployeeRead(EmployeeBase):
    pass
