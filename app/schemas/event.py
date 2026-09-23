from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


SkillLevel = Annotated[int, Field(ge=0, le=5)]


class SkillGain(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    skill_id: str = Field(min_length=1)
    gain: int = Field(default=1, ge=0)
    max_level: SkillLevel = 5


class EventBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    type: str | None = None
    format: str | None = None
    duration_hours: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    mandatory: bool = False
    target_roles: list[str] = Field(default_factory=list)
    target_grades: list[str] = Field(default_factory=list)
    develops_skills: list[SkillGain] = Field(default_factory=list)
    prerequisites: dict[str, SkillLevel] = Field(default_factory=dict)
    upcoming_sessions: list[str] = Field(default_factory=list)


class EventRead(EventBase):
    pass
