from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from threading import Lock, RLock
from typing import Any, Iterator
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, QuestPlan, QuestProgress, QuestStepProgress
from app.services.llm_service import generate_quest_steps


_quest_write_lock = RLock()
_plan_lock_guard = Lock()
_plan_locks: dict[tuple[str, str], Any] = {}
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
    previously_completed = _has_completed(db, employee_id, event_id, progress)
    if event_id not in RECURRING_EVENTS and previously_completed:
        raise HTTPException(status_code=409, detail="Quest already completed")
    if previously_completed and (progress is None or progress.status == "completed"):
        # Keep the agreed plan, but start a fresh participation in the recurring club.
        db.query(QuestStepProgress).filter_by(employee_id=employee_id, event_id=event_id).delete()
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


def _completed_step_numbers(db: Session, employee_id: str, event_id: str) -> set[int]:
    return {
        row.step_number for row in db.query(QuestStepProgress).filter_by(
            employee_id=employee_id, event_id=event_id, status="completed",
        ).all()
    }


def quest_step_counts(db: Session, employee_id: str, event_id: str) -> tuple[int, int]:
    plan = db.get(QuestPlan, (employee_id, event_id))
    if plan is None:
        return 0, 0
    expected = {step["step"] for step in plan.steps}
    return len(expected & _completed_step_numbers(db, employee_id, event_id)), len(expected)


def require_completed_quest_steps(db: Session, employee_id: str, event_id: str) -> None:
    completed, total = quest_step_counts(db, employee_id, event_id)
    if total and completed != total:
        raise HTTPException(status_code=409, detail="Complete all quest steps before finishing the quest")


def _plan_response(db: Session, plan: QuestPlan) -> dict[str, Any]:
    completed = _completed_step_numbers(db, plan.employee_id, plan.event_id)
    steps = [{**step, "done": step["step"] in completed} for step in plan.steps]
    completed_count = sum(step["done"] for step in steps)
    progress = db.query(QuestProgress).filter_by(employee_id=plan.employee_id, event_id=plan.event_id).first()
    status = progress.status if progress is not None else "recommended"
    if status == "recommended":
        history = db.query(ActivityHistory).filter_by(employee_id=plan.employee_id, event_id=plan.event_id)
        if history.filter(ActivityHistory.status.in_(ACTIVE_HISTORY_STATUSES)).first():
            status = "in_progress"
        elif history.filter_by(status="completed").first():
            status = "completed"
    return {
        "employee_id": plan.employee_id, "event_id": plan.event_id,
        "title": plan.task["title"], "provider": plan.provider, "language": plan.language,
        "task": plan.task, "steps": steps, "completed_steps": completed_count,
        "total_steps": len(steps), "completion_pct": round(completed_count / len(steps) * 100),
        "status": status, "can_complete": completed_count == len(steps) and status != "completed",
    }


def _validated_plan_steps(generated: Any) -> list[dict[str, Any]]:
    """Only persist a stable, numbered checklist; generated done flags are ignored."""
    steps = generated.get("steps") if isinstance(generated, dict) else None
    if not isinstance(steps, list) or not 3 <= len(steps) <= 5:
        raise HTTPException(status_code=502, detail="Unable to create a valid quest plan")
    result = []
    for number, step in enumerate(steps, start=1):
        if (
            not isinstance(step, dict)
            or type(step.get("step")) is not int
            or step["step"] != number
            or any(not isinstance(step.get(field), str) or not step[field].strip() for field in ("title", "description"))
        ):
            raise HTTPException(status_code=502, detail="Unable to create a valid quest plan")
        result.append({"step": number, "title": step["title"].strip(), "description": step["description"].strip()})
    return result


def get_quest_steps(employee_id: str, event_id: str, language: str | None = None) -> dict[str, Any]:
    if language is not None and language not in {"ru", "kk", "en"}:
        raise HTTPException(status_code=422, detail="language must be ru, kk or en")
    with SessionLocal() as db:
        if db.get(Employee, employee_id) is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        if db.get(Event, event_id) is None:
            raise HTTPException(status_code=404, detail="Event not found")
        plan = db.get(QuestPlan, (employee_id, event_id))
        if plan is not None:
            return _plan_response(db, plan)

    # A model call never holds the database write lock. Requests for the same
    # employee/event share generation; existing plans are always served unchanged.
    with _plan_lock_guard:
        lock = _plan_locks.setdefault((employee_id, event_id), RLock())
    with lock:
        with SessionLocal() as db:
            plan = db.get(QuestPlan, (employee_id, event_id))
            if plan is not None:
                return _plan_response(db, plan)
            employee, event, _progress = _quest_records(db, employee_id, event_id)
            plan_language = language or employee.preferred_language or "ru"
            if plan_language not in {"ru", "kk", "en"}:
                plan_language = "ru"
            task = {
                "event_id": event.event_id, "title": event.title, "description": event.description,
                "type": event.type, "format": event.format, "duration_hours": event.duration_hours,
                "develops_skills": event.develops_skills or [],
            }
            event_context = {**task, "prerequisites": event.prerequisites or {}}
            employee_context = {
                "employee_id": employee.employee_id, "role": employee.role, "grade": employee.grade,
                "career_goal": employee.career_goal, "skills": employee.skills,
            }
        generated = generate_quest_steps(event_context, employee_context, language=plan_language)
        steps = _validated_plan_steps(generated)
        with quest_write_transaction() as db:
            _quest_records(db, employee_id, event_id)
            plan = db.get(QuestPlan, (employee_id, event_id))
            if plan is None:
                plan = QuestPlan(
                    employee_id=employee_id, event_id=event_id, task=task, steps=steps,
                    provider="openai" if generated.get("provider") == "openai" else "template",
                    language=plan_language,
                )
                db.add(plan)
                # Old markers were created against regenerated, unpersisted plans;
                # they cannot safely identify a step in this newly stored plan.
                db.query(QuestStepProgress).filter_by(employee_id=employee_id, event_id=event_id).delete()
                db.flush()
            return _plan_response(db, plan)


def complete_quest_step(employee_id: str, event_id: str, step_number: int) -> dict[str, Any]:
    if type(step_number) is not int or step_number < 1:
        raise HTTPException(status_code=422, detail="Unknown quest step")
    with quest_write_transaction() as db:
        _employee, _event, progress = _quest_records(db, employee_id, event_id)
        plan = db.get(QuestPlan, (employee_id, event_id))
        if plan is None:
            raise HTTPException(status_code=409, detail="Open the quest plan before completing its steps")
        if step_number not in {step["step"] for step in plan.steps}:
            raise HTTPException(status_code=422, detail="Unknown quest step")
        row = db.query(QuestStepProgress).filter_by(
            employee_id=employee_id, event_id=event_id, step_number=step_number,
        ).first()
        if progress is not None and progress.status == "completed":
            if row is None or row.status != "completed":
                raise HTTPException(status_code=409, detail="Quest already completed")
        else:
            active = db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).filter(
                ActivityHistory.status.in_(ACTIVE_HISTORY_STATUSES)
            ).first()
            if active is None and (progress is None or progress.status != "selected"):
                raise HTTPException(status_code=409, detail="Select the quest before completing its steps")
            _select_quest(db, employee_id, event_id, progress.mode if progress else "solo")
            if row is None:
                row = QuestStepProgress(employee_id=employee_id, event_id=event_id, step_number=step_number)
                db.add(row)
            row.status = "completed"
            row.completed_at = row.completed_at or date.today()
            db.flush()
            completed, total = quest_step_counts(db, employee_id, event_id)
            for history in db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).filter(
                ActivityHistory.status.in_(ACTIVE_HISTORY_STATUSES)
            ).all():
                history.completion_pct = round(completed / total * 100)
            db.flush()
        result = _plan_response(db, plan)
        return {
            "employee_id": employee_id, "event_id": event_id, "step_number": step_number, "status": "completed",
            "completed_steps": result["completed_steps"], "total_steps": result["total_steps"],
            "completion_pct": result["completion_pct"], "can_complete": result["can_complete"],
        }
