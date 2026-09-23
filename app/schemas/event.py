from __future__ import annotations

from pydantic import BaseModel, Field


class SkillGain(BaseModel):
    skill_id: str
    gain: int = 1
    max_level: int = 5


class EventBase(BaseModel):
    event_id: str
    title: str
    description: str | None = None
    type: str | None = None
    format: str | None = None
    duration_hours: float | None = None
    mandatory: bool = False
    target_roles: list[str] = Field(default_factory=list)
    target_grades: list[str] = Field(default_factory=list)
    develops_skills: list[SkillGain] = Field(default_factory=list)
    prerequisites: dict[str, int] = Field(default_factory=dict)
    upcoming_sessions: list[str] = Field(default_factory=list)


class EventRead(EventBase):
    pass
