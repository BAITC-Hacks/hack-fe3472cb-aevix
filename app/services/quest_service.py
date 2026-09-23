from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException

from app.db.database import SessionLocal
from app.db.models import Employee, Event, QuestProgress


def select_quest(employee_id: str, event_id: str, mode: str = "solo") -> dict[str, Any]:
    if mode not in {"solo", "team"}:
        raise HTTPException(status_code=422, detail="mode must be solo or team")
    db = SessionLocal()
    try:
        if not db.get(Employee, employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")
        event = db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        progress = db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).first()
        if progress is None:
            progress = QuestProgress(employee_id=employee_id, event_id=event_id, status="selected", mode=mode)
            db.add(progress)
        else:
            progress.status = "selected"
            progress.mode = mode
        db.commit()
        return {
            "employee_id": employee_id,
            "event_id": event_id,
            "title": event.title,
            "status": progress.status,
            "mode": progress.mode,
            "next_step": "Start the quest and complete the activity.",
        }
    finally:
        db.close()


def mark_quest_completed(employee_id: str, event_id: str) -> None:
    db = SessionLocal()
    try:
        progress = db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).first()
        if progress is None:
            progress = QuestProgress(employee_id=employee_id, event_id=event_id, status="completed", mode="solo")
            db.add(progress)
        else:
            progress.status = "completed"
            progress.completed_at = date.today()
        db.commit()
    finally:
        db.close()
