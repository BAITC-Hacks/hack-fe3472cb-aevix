from __future__ import annotations

from pydantic import BaseModel, Field


class GameNode(BaseModel):
    id: str
    title: str
    status: str


class CityProgress(BaseModel):
    level: int = Field(default=1, ge=1, le=10)
    max_level: int = 10
    completed_courses: int = Field(default=0, ge=0)
    courses_per_level: int = 2
    courses_to_next_level: int = Field(default=2, ge=0, le=2)
    progress_to_next_level: int = Field(default=0, ge=0, le=100)


class GameMap(BaseModel):
    employee_id: str
    current_zone: str | None = None
    target_zone: str | None = None
    career_level: int = 0
    city_level: int = Field(default=1, ge=1, le=10)
    city_progress: CityProgress = Field(default_factory=CityProgress)
    progress_to_next_grade: float = 0.0
    nodes: list[GameNode] = Field(default_factory=list)
    recommended_quest_ids: list[str] = Field(default_factory=list)
