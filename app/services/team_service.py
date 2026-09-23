from __future__ import annotations

from datetime import date
from uuid import uuid4
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Employee, Event, Team, TeamMember
from app.services.recommendation_service import complete_quest


def _get_team(db: Session, team_id: str) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def create_team(payload: dict[str, Any]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        creator_id = payload.get("creator_id")
        if not db.get(Employee, creator_id):
            raise HTTPException(status_code=404, detail="Creator employee not found")
        team_id = f"TEAM_{uuid4().hex[:10]}"
        team = Team(team_id=team_id, name=payload.get("name", "Career Quest Team"), creator_id=creator_id, max_members=int(payload.get("max_members", 5)))
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
    db = SessionLocal()
    try:
        team = _get_team(db, team_id)
        if not db.get(Event, event_id):
            raise HTTPException(status_code=404, detail="Event not found")
        team.status = "in_progress"
        db.commit()
        return {**get_team(team_id), "current_quest": {"event_id": event_id, "status": "in_progress", "started_at": date.today().isoformat()}}
    finally:
        db.close()


def complete_team_quest(team_id: str, event_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        team = _get_team(db, team_id)
        members = db.query(TeamMember).filter_by(team_id=team_id).all()
        if not members:
            raise HTTPException(status_code=409, detail="Team has no members")
        team.completed_team_quests += 1
        team.status = "waiting_for_member" if team.completed_team_quests >= 3 else "active"
        db.commit()
        member_results = [complete_quest(member.employee_id, event_id) for member in members]
        return {**get_team(team_id), "event_id": event_id, "member_results": member_results}
    finally:
        db.close()


def set_team_status(team_id: str, status: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        team = _get_team(db, team_id)
        team.status = status
        db.commit()
        return get_team(team_id)
    finally:
        db.close()
