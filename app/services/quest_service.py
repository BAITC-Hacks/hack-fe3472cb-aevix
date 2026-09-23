from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, QuestProgress


def completion_is_current(event: Event, history: list[ActivityHistory]) -> bool:
    """Allow another annual assignment or club session without duplicate rewards."""
    completed = [entry for entry in history if entry.status == "completed"]
    if event.mandatory:
        return any(entry.date and entry.date.year == date.today().year for entry in completed)
    if event.event_id == "EV_036":
        return any(entry.date == date.today() for entry in completed)
    return bool(completed)


def _select_quest(db: Session, employee_id: str, event_id: str, mode: str = "solo") -> dict[str, Any]:
    if mode not in {"solo", "team"}:
        raise HTTPException(status_code=422, detail="mode must be solo or team")
    if not db.get(Employee, employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    history = db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).all()
    if completion_is_current(event, history):
        raise HTTPException(status_code=409, detail="Quest already completed")
    progress = db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).first()
    if progress is None:
        progress = QuestProgress(employee_id=employee_id, event_id=event_id, status="selected", mode=mode)
        db.add(progress)
    else:
        progress.status = "selected"
        progress.mode = mode
    progress.started_at = progress.started_at or date.today()
    progress.completed_at = None
    if not any(entry.status in {"selected", "registered", "in_progress", "overdue"} for entry in history):
        db.add(ActivityHistory(
            record_id=f"R_{uuid4().hex}", employee_id=employee_id, event_id=event_id,
            date=date.today(), status="in_progress", completion_pct=0, assigned_by="self",
        ))
    return {
        "employee_id": employee_id,
        "event_id": event_id,
        "title": event.title,
        "status": progress.status,
        "mode": progress.mode,
        "next_step": "Continue the quest in My Learning and complete the activity.",
    }


def select_quest(employee_id: str, event_id: str, mode: str = "solo") -> dict[str, Any]:
    with SessionLocal.begin() as db:
        return _select_quest(db, employee_id, event_id, mode)


def mark_quest_completed(employee_id: str, event_id: str, db: Session) -> None:
    progress = db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).first()
    if progress is None:
        progress = QuestProgress(employee_id=employee_id, event_id=event_id, status="completed", mode="solo")
        db.add(progress)
    progress.status = "completed"
    progress.completed_at = date.today()
