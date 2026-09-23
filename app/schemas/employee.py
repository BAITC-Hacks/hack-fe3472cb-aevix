from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class CareerGoal(BaseModel):
    target_role: str | None = None
    target_grade: str | None = None


class EmployeeBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    employee_id: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    department: str | None = None
    role: str | None = None
    grade: str | None = None
    manager_id: str | None = None
    hire_date: date | None = None
    tenure_months: int | None = Field(default=None, ge=0)
    work_format: str | None = None
    preferred_language: str | None = None
    career_goal: CareerGoal | None = None
    skills: dict[str, Annotated[int, Field(strict=True, ge=0, le=5)]] = Field(default_factory=dict)
    last_review_date: date | None = None


class EmployeeRead(EmployeeBase):
    pass


class QuestSelection(BaseModel):
    mode: Literal["solo", "team"] = "solo"
