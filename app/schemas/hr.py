from __future__ import annotations

from pydantic import BaseModel, Field


class TopSkillGap(BaseModel):
    skill_id: str
    skill_name: str
    affected_employees: int
    average_gap: float


class HRDashboard(BaseModel):
    total_employees: int
    average_progress_to_next_grade: float
    top_skill_gaps: list[TopSkillGap] = Field(default_factory=list)
    inactive_employees_count: int
    events_completion_rate: float
    popular_events: list[dict] = Field(default_factory=list)
    risky_segments: list[str] = Field(default_factory=list)
