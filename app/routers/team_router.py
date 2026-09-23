from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.db.auth_models import AuthSession
from app.db.database import SessionLocal
from app.db.models import TeamMember
from app.services.auth_service import assert_employee_access, require_session

from app.schemas.collaboration import TeamCreate, TeamJoin
from app.services.team_service import create_team, complete_team_quest, get_team, join_team, set_team_status, start_team_quest

router = APIRouter(dependencies=[Depends(require_session)])


def team_reader(team_id: str, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    team = get_team(team_id)
    if session.role != "hr" and session.employee_id not in team["member_ids"]:
        raise HTTPException(403, "Team access is limited to its members")
    return team


def team_actor(team_id: str, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    if session.role == "hr":
        raise HTTPException(403, "HR preview is read-only")
    return team_reader(team_id, session)


@router.get("")
def list_teams(employee_id: str | None = None, session: AuthSession = Depends(require_session)) -> list[dict[str, Any]]:
    employee_id = employee_id or session.employee_id
    if not employee_id:
        return []
    assert_employee_access(session, employee_id)
    with SessionLocal() as db:
        team_ids = [row.team_id for row in db.query(TeamMember).filter_by(employee_id=employee_id).all()]
    return [get_team(team_id) for team_id in team_ids]


@router.post("")
def create(payload: TeamCreate, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    assert_employee_access(session, payload.creator_id, allow_hr=False)
    return create_team(payload.model_dump())


@router.get("/{team_id}")
def read(team: dict = Depends(team_reader)) -> dict[str, Any]:
    return team


@router.post("/{team_id}/join")
def join(team_id: str, payload: TeamJoin, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    assert_employee_access(session, payload.employee_id, allow_hr=False)
    return join_team(team_id, payload.employee_id)


@router.post("/{team_id}/quests/{event_id}/start")
def start(team_id: str, event_id: str, _team: dict = Depends(team_actor)) -> dict[str, Any]:
    return start_team_quest(team_id, event_id)


@router.post("/{team_id}/quests/{event_id}/complete")
def complete(team_id: str, event_id: str, _team: dict = Depends(team_actor)) -> dict[str, Any]:
    return complete_team_quest(team_id, event_id)


@router.post("/{team_id}/pause")
def pause(team_id: str, _team: dict = Depends(team_actor)) -> dict[str, Any]:
    return set_team_status(team_id, "paused")


@router.post("/{team_id}/resume")
def resume(team_id: str, _team: dict = Depends(team_actor)) -> dict[str, Any]:
    return set_team_status(team_id, "active")
