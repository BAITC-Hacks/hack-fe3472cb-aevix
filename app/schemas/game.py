from __future__ import annotations

from pydantic import BaseModel, Field


class GameNode(BaseModel):
    id: str
    title: str
    status: str


class GameMap(BaseModel):
    employee_id: str
    current_zone: str | None = None
    target_zone: str | None = None
    career_level: int = 0
    progress_to_next_grade: float = 0.0
    nodes: list[GameNode] = Field(default_factory=list)
    recommended_quest_ids: list[str] = Field(default_factory=list)
