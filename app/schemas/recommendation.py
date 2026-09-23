from __future__ import annotations

from pydantic import BaseModel, Field


class AffectedSkill(BaseModel):
    skill_id: str
    skill_name: str
    current_level: int
    required_level: int
    gain: int
    max_level: int
    expected_after: int
    gap_before: int
    gap_after: int


class RecommendationItem(BaseModel):
    event_id: str
    quest_title: str
    quest_type: str | None = None
    format: str | None = None
    duration_hours: float | None = None
    score: float
    priority: str
    affected_skills: list[AffectedSkill]
    reason: str
    game_message: str


class RecommendationResponse(BaseModel):
    employee_id: str
    role: str | None = None
    current_grade: str | None = None
    target_role: str | None = None
    target_grade: str | None = None
    progress_to_next_grade: float
    recommendations: list[RecommendationItem] = Field(default_factory=list)
