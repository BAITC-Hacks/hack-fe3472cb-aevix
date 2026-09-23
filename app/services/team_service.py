from __future__ import annotations

from datetime import date
from uuid import uuid4
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Employee, Event, Team, TeamMember
from app.services.quest_service import _select_quest
from app.services.recommendation_service import _complete_quest


def _get_team(db: Session, team_id: str) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def create_team(payload: dict[str, Any]) -> dict[str, Any]:
    capacity = payload.get("max_members", 5)
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise HTTPException(status_code=422, detail="max_members must be a positive integer")
    name = payload.get("name", "Career Quest Team")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=422, detail="Team name is required")
    db = SessionLocal()
    try:
        creator_id = payload.get("creator_id")
        if not db.get(Employee, creator_id):
            raise HTTPException(status_code=404, detail="Creator employee not found")
        team_id = f"TEAM_{uuid4().hex[:10]}"
        team = Team(team_id=team_id, name=name.strip(), creator_id=creator_id, max_members=capacity)
        db.add(team)
        db.add(TeamMember(team_id=team_id, employee_id=creator_id))
        db.commit()
        return get_team(team_id)
    finally:
        db.close()


def get_team(team_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        team = _get_team(db, team_id)
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        return {
            "team_id": team.team_id,
            "name": team.name,
            "creator_id": team.creator_id,
            "max_members": team.max_members,
            "status": team.status,
            "completed_team_quests": team.completed_team_quests,
            "member_ids": [member.employee_id for member in members],
        }
    finally:
        db.close()


def join_team(team_id: str, employee_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        team = _get_team(db, team_id)
        if not db.get(Employee, employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        if any(member.employee_id == employee_id for member in members):
            return get_team(team_id)
        if len(members) >= team.max_members:
            raise HTTPException(status_code=409, detail="Team is full")
        db.add(TeamMember(team_id=team_id, employee_id=employee_id))
        if team.status == "waiting_for_member":
            team.status = "active"
        db.commit()
        return get_team(team_id)
    finally:
        db.close()


def start_team_quest(team_id: str, event_id: str) -> dict[str, Any]:
    with SessionLocal.begin() as db:
        team = _get_team(db, team_id)
        if not db.get(Event, event_id):
            raise HTTPException(status_code=404, detail="Event not found")
        if team.status in {"paused", "waiting_for_member"}:
            raise HTTPException(status_code=409, detail="Team must be active to start a quest")
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        if not members:
            raise HTTPException(status_code=409, detail="Team has no members")
        for member in members:
            _select_quest(db, member.employee_id, event_id, "team")
        team.status = "in_progress"
    return {**get_team(team_id), "current_quest": {"event_id": event_id, "status": "in_progress", "started_at": date.today().isoformat()}}


def complete_team_quest(team_id: str, event_id: str) -> dict[str, Any]:
    with SessionLocal.begin() as db:
        team = _get_team(db, team_id)
        if not db.get(Event, event_id):
            raise HTTPException(status_code=404, detail="Event not found")
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        if not members:
            raise HTTPException(status_code=409, detail="Team has no members")
        # A failed or repeated member completion must not leave partial rewards
        # or increment the team counter.
        member_results = [_complete_quest(db, member.employee_id, event_id) for member in members]
        team.completed_team_quests += 1
        team.status = "waiting_for_member" if team.completed_team_quests >= 3 else "active"
    return {**get_team(team_id), "event_id": event_id, "member_results": member_results}


def set_team_status(team_id: str, status: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        team = _get_team(db, team_id)
        team.status = status
        db.commit()
        return get_team(team_id)
    finally:
        db.close()
