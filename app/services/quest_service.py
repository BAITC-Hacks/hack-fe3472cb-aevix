from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, QuestProgress


_quest_write_lock = RLock()
RECURRING_EVENTS = {"EV_036"}
ACTIVE_HISTORY_STATUSES = {"registered", "in_progress", "overdue"}


@contextmanager
def quest_write_transaction() -> Iterator[Session]:
    """Keep a quest and its learning history/rewards in a single transaction."""
    with _quest_write_lock:
        with SessionLocal() as db:
            try:
                # Acquire SQLite's write lock before checking completion, including
                # across server workers. Other databases lock the employee row.
                if db.get_bind().dialect.name == "sqlite":
                    db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise


def quest_prerequisites_met(employee: Employee, event: Event) -> bool:
    return all(
        int((employee.skills or {}).get(skill_id, 0)) >= int(level)
        for skill_id, level in (event.prerequisites or {}).items()
    )


def _quest_records(db: Session, employee_id: str, event_id: str) -> tuple[Employee, Event, QuestProgress | None]:
    employee = db.query(Employee).filter_by(employee_id=employee_id).with_for_update().first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if not quest_prerequisites_met(employee, event):
        raise HTTPException(status_code=409, detail="Quest prerequisites are not met")
    progress = db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).first()
    return employee, event, progress


def _has_completed(db: Session, employee_id: str, event_id: str, progress: QuestProgress | None) -> bool:
    return bool(
        (progress is not None and progress.status == "completed")
        or db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id, status="completed").first()
    )


def _select_quest(db: Session, employee_id: str, event_id: str, mode: str = "solo") -> dict[str, Any]:
    if mode not in {"solo", "team"}:
        raise HTTPException(status_code=422, detail="mode must be solo or team")
    _employee, event, progress = _quest_records(db, employee_id, event_id)
    if event_id not in RECURRING_EVENTS and _has_completed(db, employee_id, event_id, progress):
        raise HTTPException(status_code=409, detail="Quest already completed")
    if progress is None:
        progress = QuestProgress(employee_id=employee_id, event_id=event_id)
        db.add(progress)
    progress.status = "selected"
    progress.mode = mode
    progress.started_at = progress.started_at or date.today()
    progress.completed_at = None

    active = db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).filter(
        ActivityHistory.status.in_(ACTIVE_HISTORY_STATUSES)
    ).all()
    if not active:
        active = [ActivityHistory(
            record_id=f"R_{uuid4().hex}", employee_id=employee_id, event_id=event_id,
            date=date.today(), completion_pct=0, assigned_by="self",
        )]
        db.add(active[0])
    for entry in active:
        entry.status = "in_progress"
        entry.date = entry.date or date.today()
    db.flush()
    return {
        "employee_id": employee_id, "event_id": event_id, "title": event.title,
        "status": progress.status, "mode": progress.mode,
        "next_step": "Start the quest and complete the activity.",
    }


def select_quest(employee_id: str, event_id: str, mode: str = "solo") -> dict[str, Any]:
    with quest_write_transaction() as db:
        return _select_quest(db, employee_id, event_id, mode)


def mark_quest_completed(employee_id: str, event_id: str, db: Session | None = None) -> None:
    if db is None:
        with quest_write_transaction() as transaction:
            mark_quest_completed(employee_id, event_id, transaction)
        return
    progress = db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).first()
    if progress is None:
        progress = QuestProgress(employee_id=employee_id, event_id=event_id, mode="solo", started_at=date.today())
        db.add(progress)
    progress.status = "completed"
    progress.completed_at = date.today()
    db.flush()
