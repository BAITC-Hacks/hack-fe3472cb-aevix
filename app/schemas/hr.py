from __future__ import annotations

from pydantic import BaseModel, Field


class TopSkillGap(BaseModel):
    skill_id: str
    skill_name: str
    affected_employees: int
    average_gap: float


class ESGEngagementSummary(BaseModel):
    total_contributed_coins: int = 0
    contributors_count: int = 0


class TeamQuestActivity(BaseModel):
    teams_count: int = 0
    completed_team_quests: int = 0


class HRDashboard(BaseModel):
    total_employees: int
    average_progress_to_next_grade: float
    top_skill_gaps: list[TopSkillGap] = Field(default_factory=list)
    inactive_employees_count: int
    events_completion_rate: float
    popular_events: list[dict] = Field(default_factory=list)
    risky_segments: list[str] = Field(default_factory=list)
    employees_without_recommendations: list[str] = Field(default_factory=list)
    participation_by_activity: list[dict] = Field(default_factory=list)
    esg_engagement: ESGEngagementSummary = Field(default_factory=ESGEngagementSummary)
    team_quest_activity: TeamQuestActivity = Field(default_factory=TeamQuestActivity)
