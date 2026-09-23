from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, StrictInt

from app.services.team_service import create_team, complete_team_quest, get_team, join_team, set_team_status, start_team_quest

router = APIRouter()


class CreateTeamRequest(BaseModel):
    creator_id: str = Field(min_length=1)
    name: str = Field(default="Career Quest Team", min_length=1)
    max_members: StrictInt = Field(default=5, ge=1)


class JoinTeamRequest(BaseModel):
    employee_id: str = Field(min_length=1)


@router.post("")
def create(payload: CreateTeamRequest) -> dict[str, Any]:
    return create_team(payload.model_dump())


@router.get("/{team_id}")
def read(team_id: str) -> dict[str, Any]:
    return get_team(team_id)


@router.post("/{team_id}/join")
def join(team_id: str, payload: JoinTeamRequest) -> dict[str, Any]:
    return join_team(team_id, payload.employee_id)


@router.post("/{team_id}/quests/{event_id}/start")
def start(team_id: str, event_id: str) -> dict[str, Any]:
    return start_team_quest(team_id, event_id)


@router.post("/{team_id}/quests/{event_id}/complete")
def complete(team_id: str, event_id: str) -> dict[str, Any]:
    return complete_team_quest(team_id, event_id)


@router.post("/{team_id}/pause")
def pause(team_id: str) -> dict[str, Any]:
    return set_team_status(team_id, "paused")


@router.post("/{team_id}/resume")
def resume(team_id: str) -> dict[str, Any]:
    return set_team_status(team_id, "active")
