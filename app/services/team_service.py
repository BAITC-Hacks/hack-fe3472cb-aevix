from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Employee, Event, Team, TeamMember
from app.schemas.collaboration import TeamCreate
from app.services.quest_service import _select_quest, quest_write_transaction
from app.services.recommendation_service import _complete_quest


def _get_team(db: Session, team_id: str) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def _team_snapshot(db: Session, team: Team) -> dict[str, Any]:
    members = db.query(TeamMember).filter_by(team_id=team.team_id).order_by(TeamMember.id).all()
    current_quest = None
    if team.current_event_id:
        current_quest = {
            "event_id": team.current_event_id,
            "status": "paused" if team.status == "paused" else "in_progress",
            "started_at": team.quest_started_at.isoformat() if team.quest_started_at else None,
        }
    return {
        "team_id": team.team_id,
        "name": team.name,
        "creator_id": team.creator_id,
        "max_members": team.max_members,
        "status": team.status,
        "completed_team_quests": team.completed_team_quests,
        "member_ids": [member.employee_id for member in members],
        "current_quest": current_quest,
    }


def create_team(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = TeamCreate.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with quest_write_transaction() as db:
        if not db.get(Employee, request.creator_id):
            raise HTTPException(status_code=404, detail="Creator employee not found")
        team = Team(team_id=f"TEAM_{uuid4().hex[:10]}", **request.model_dump())
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.team_id, employee_id=team.creator_id))
        db.flush()
        return _team_snapshot(db, team)


def get_team(team_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        return _team_snapshot(db, _get_team(db, team_id))


def join_team(team_id: str, employee_id: str) -> dict[str, Any]:
    with quest_write_transaction() as db:
        team = _get_team(db, team_id)
        if not db.get(Employee, employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        if any(member.employee_id == employee_id for member in members):
            return _team_snapshot(db, team)
        if team.status not in {"active", "waiting_for_member"}:
            raise HTTPException(status_code=409, detail="Members can join only an active team or one waiting for a member")
        if len(members) >= team.max_members:
            raise HTTPException(status_code=409, detail="Team is full")
        db.add(TeamMember(team_id=team_id, employee_id=employee_id))
        if team.status == "waiting_for_member":
            team.status = "active"
        db.flush()
        return _team_snapshot(db, team)


def start_team_quest(team_id: str, event_id: str) -> dict[str, Any]:
    with quest_write_transaction() as db:
        team = _get_team(db, team_id)
        if not db.get(Event, event_id):
            raise HTTPException(status_code=404, detail="Event not found")
        if team.status != "active" or team.current_event_id:
            raise HTTPException(status_code=409, detail="Team must be active with no current quest before starting")
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        if not members:
            raise HTTPException(status_code=409, detail="Team has no members")
        for member in members:
            _select_quest(db, member.employee_id, event_id, mode="team")
        team.status = "in_progress"
        team.current_event_id = event_id
        team.quest_started_at = date.today()
        db.flush()
        return _team_snapshot(db, team)


def complete_team_quest(team_id: str, event_id: str) -> dict[str, Any]:
    with quest_write_transaction() as db:
        team = _get_team(db, team_id)
        if not db.get(Event, event_id):
            raise HTTPException(status_code=404, detail="Event not found")
        if team.status != "in_progress" or team.current_event_id != event_id:
            raise HTTPException(status_code=409, detail="Only the team's current, in-progress quest can be completed")
        members = db.query(TeamMember).filter_by(team_id=team_id).order_by(TeamMember.id).all()
        if not members:
            raise HTTPException(status_code=409, detail="Team has no members")
        member_results = [_complete_quest(db, member.employee_id, event_id) for member in members]
        team.completed_team_quests += 1
        # A full team cannot recruit another member, so keep it able to continue.
        needs_member = team.completed_team_quests % 3 == 0 and len(members) < team.max_members
        team.status = "waiting_for_member" if needs_member else "active"
        team.current_event_id = None
        team.quest_started_at = None
        db.flush()
        return {**_team_snapshot(db, team), "event_id": event_id, "member_results": member_results}


def set_team_status(team_id: str, status: str) -> dict[str, Any]:
    if status not in {"paused", "active"}:
        raise HTTPException(status_code=422, detail="status must be paused or active")
    with quest_write_transaction() as db:
        team = _get_team(db, team_id)
        if status == "paused":
            if team.status not in {"active", "in_progress"}:
                raise HTTPException(status_code=409, detail="Only an active or in-progress team can be paused")
            team.status = "paused"
        else:
            if team.status != "paused":
                raise HTTPException(status_code=409, detail="Only a paused team can be resumed")
            team.status = "in_progress" if team.current_event_id else "active"
        db.flush()
        return _team_snapshot(db, team)
