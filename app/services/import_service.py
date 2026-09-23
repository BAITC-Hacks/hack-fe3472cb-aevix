import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, RoleProfile, Skill


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value: Any) -> date | None:
    if value in (None, "", "nan"):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _json_load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def import_dataset_from_path(dataset_dir: str | None = None) -> dict[str, Any]:
    resolved_dir = Path(dataset_dir or settings.dataset_dir)
    if not resolved_dir.exists():
        raise HTTPException(status_code=404, detail=f"Dataset directory not found: {resolved_dir}")

    employees_path = resolved_dir / "employees.json"
    events_path = resolved_dir / "events.json"
    skills_path = resolved_dir / "skills.json"
    history_path = resolved_dir / "activity_history.csv"

    results = {
        "employees": import_employees(employees_path),
        "events": import_events(events_path),
        "skills": import_skills(skills_path),
        "history": import_history(history_path),
    }
    return results


def seed_demo_data() -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        has_data = db.query(Employee).first() is not None
        if has_data:
            return {"status": "already_seeded", "employees": db.query(Employee).count()}
        default_dataset = settings.dataset_path
        return import_dataset_from_path(str(default_dataset))
    finally:
        db.close()


def import_employees(file_path: str | Path) -> int:
    path = Path(file_path)
    payload = _json_load(path)
    employees = payload.get("employees", [])
    db: Session = SessionLocal()
    try:
        for item in employees:
            record = db.get(Employee, item["employee_id"])
            data = {
                "employee_id": item["employee_id"],
                "full_name": item.get("full_name"),
                "department": item.get("department"),
                "role": item.get("role"),
                "grade": item.get("grade"),
                "manager_id": item.get("manager_id"),
                "hire_date": _parse_date(item.get("hire_date")),
                "tenure_months": item.get("tenure_months"),
                "work_format": item.get("work_format"),
                "preferred_language": item.get("preferred_language"),
                "career_goal": item.get("career_goal"),
                "skills": item.get("skills", {}),
                "last_review_date": _parse_date(item.get("last_review_date")),
            }
            if record is None:
                db.add(Employee(**data))
            else:
                for key, value in data.items():
                    setattr(record, key, value)
        db.commit()
        return len(employees)
    finally:
        db.close()


def register_employee(payload: dict[str, Any]) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employee_id = payload.get("employee_id")
        if not employee_id or not payload.get("full_name"):
            raise HTTPException(status_code=422, detail="employee_id and full_name are required")
        record = db.get(Employee, employee_id)
        data = {
            "employee_id": employee_id,
            "full_name": payload["full_name"],
            "department": payload.get("department"),
            "role": payload.get("role"),
            "grade": payload.get("grade"),
            "manager_id": payload.get("manager_id"),
            "hire_date": _parse_date(payload.get("hire_date")),
            "tenure_months": payload.get("tenure_months"),
            "work_format": payload.get("work_format"),
            "preferred_language": payload.get("preferred_language"),
            "career_goal": payload.get("career_goal"),
            "skills": payload.get("skills", {}),
            "last_review_date": _parse_date(payload.get("last_review_date")),
        }
        if record is None:
            db.add(Employee(**data))
        else:
            for key, value in data.items():
                setattr(record, key, value)
        db.commit()
        return {"status": "registered", "employee_id": employee_id, "updated": record is not None}
    finally:
        db.close()


def import_events(file_path: str | Path) -> int:
    path = Path(file_path)
    payload = _json_load(path)
    events = payload.get("events", [])
    db: Session = SessionLocal()
    try:
        for item in events:
            record = db.get(Event, item["event_id"])
            data = {
                "event_id": item["event_id"],
                "title": item.get("title"),
                "description": item.get("description"),
                "type": item.get("type"),
                "format": item.get("format"),
                "duration_hours": item.get("duration_hours"),
                "mandatory": bool(item.get("mandatory", False)),
                "target_roles": item.get("target_roles", []),
                "target_grades": item.get("target_grades", []),
                "develops_skills": item.get("develops_skills", []),
                "prerequisites": item.get("prerequisites", {}),
                "upcoming_sessions": item.get("upcoming_sessions", []),
            }
            if record is None:
                db.add(Event(**data))
            else:
                for key, value in data.items():
                    setattr(record, key, value)
        db.commit()
        return len(events)
    finally:
        db.close()


def import_skills(file_path: str | Path) -> int:
    path = Path(file_path)
    payload = _json_load(path)
    skills = payload.get("skills", [])
    role_profiles = payload.get("role_profiles", [])
    db: Session = SessionLocal()
    try:
        for item in skills:
            record = db.get(Skill, item["skill_id"])
            data = {
                "skill_id": item["skill_id"],
                "name": item.get("name"),
                "type": item.get("type"),
                "category": item.get("category"),
                "description": item.get("description"),
            }
            if record is None:
                db.add(Skill(**data))
            else:
                for key, value in data.items():
                    setattr(record, key, value)
        for item in role_profiles:
            profile = db.query(RoleProfile).filter_by(role=item["role"], grade=item["grade"]).first()
            data = {
                "role": item.get("role"),
                "grade": item.get("grade"),
                "required_skills": item.get("required_skills", {}),
                "critical_skills": item.get("critical_skills", []),
            }
            if profile is None:
                db.add(RoleProfile(**data))
            else:
                for key, value in data.items():
                    setattr(profile, key, value)
        db.commit()
        return len(skills) + len(role_profiles)
    finally:
        db.close()


def import_history(file_path: str | Path) -> int:
    path = Path(file_path)
    df = pd.read_csv(path)
    db: Session = SessionLocal()
    try:
        rows = 0
        for row in df.to_dict(orient="records"):
            record_id = str(row.get("record_id") or f"R_{rows}")
            record = db.get(ActivityHistory, record_id)
            data = {
                "record_id": record_id,
                "employee_id": row.get("employee_id"),
                "event_id": row.get("event_id"),
                "date": _parse_date(row.get("date")),
                "due_date": _parse_date(row.get("due_date")),
                "status": row.get("status"),
                "completion_pct": _safe_int(row.get("completion_pct"), 0) if pd.notna(row.get("completion_pct")) else None,
                "score": _safe_int(row.get("score"), 0) if pd.notna(row.get("score")) else None,
                "feedback_rating": _safe_int(row.get("feedback_rating"), 0) if pd.notna(row.get("feedback_rating")) else None,
                "assigned_by": row.get("assigned_by"),
            }
            if record is None:
                db.add(ActivityHistory(**data))
            else:
                for key, value in data.items():
                    setattr(record, key, value)
            rows += 1
        db.commit()
        return rows
    finally:
        db.close()
