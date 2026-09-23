from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException

from app.db.database import SessionLocal
from app.db.models import Employee, Event, QuestProgress, QuestStepProgress
from app.services.llm_service import generate_quest_steps


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


def get_quest_steps(employee_id: str, event_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        event = db.get(Event, event_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        result = generate_quest_steps(
            {"event_id": event.event_id, "title": event.title, "description": event.description, "type": event.type, "duration_hours": event.duration_hours, "develops_skills": event.develops_skills, "prerequisites": event.prerequisites},
            {"employee_id": employee.employee_id, "role": employee.role, "grade": employee.grade, "career_goal": employee.career_goal, "skills": employee.skills},
        )
        result["task"] = {
            "event_id": event.event_id,
            "title": event.title,
            "description": event.description,
            "type": event.type,
            "format": event.format,
            "duration_hours": event.duration_hours,
            "develops_skills": event.develops_skills or [],
        }
        completed = {row.step_number for row in db.query(QuestStepProgress).filter_by(employee_id=employee_id, event_id=event_id, status="completed").all()}
        for step in result["steps"]:
            step["done"] = step["step"] in completed
        return result
    finally:
        db.close()


def complete_quest_step(employee_id: str, event_id: str, step_number: int) -> dict[str, Any]:
    steps = get_quest_steps(employee_id, event_id)["steps"]
    if not any(step["step"] == step_number for step in steps):
        raise HTTPException(status_code=422, detail="Unknown quest step")
    db = SessionLocal()
    try:
        if not db.get(Employee, employee_id) or not db.get(Event, event_id):
            raise HTTPException(status_code=404, detail="Employee or event not found")
        row = db.query(QuestStepProgress).filter_by(employee_id=employee_id, event_id=event_id, step_number=step_number).first()
        if row is None:
            row = QuestStepProgress(employee_id=employee_id, event_id=event_id, step_number=step_number, status="completed", completed_at=date.today())
            db.add(row)
        else:
            row.status = "completed"
            row.completed_at = date.today()
        db.commit()
        completed_steps = db.query(QuestStepProgress).filter_by(employee_id=employee_id, event_id=event_id, status="completed").count()
        return {"employee_id": employee_id, "event_id": event_id, "step_number": step_number, "status": "completed", "completed_steps": completed_steps, "total_steps": len(steps)}
    finally:
        db.close()
