from __future__ import annotations

from pydantic import BaseModel


class SkillBase(BaseModel):
    skill_id: str
    name: str
    type: str
    category: str | None = None
    description: str | None = None


class SkillRead(SkillBase):
    pass


class RoleProfileRead(BaseModel):
    id: int | None = None
    role: str
    grade: str
    required_skills: dict[str, int] = {}
    critical_skills: list[str] = []
