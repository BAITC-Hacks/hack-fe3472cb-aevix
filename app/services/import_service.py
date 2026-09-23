import csv
import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, RoleProfile, Skill
from app.schemas.employee import EmployeeBase
from app.schemas.event import EventBase
from app.schemas.history import ActivityHistoryBase
from app.schemas.skill import RoleProfileRead, SkillBase


def _parse_date(value: Any) -> date | None:
    if value in (None, "", "nan"):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid date; expected YYYY-MM-DD")


@contextmanager
def import_transaction(db: Session | None = None):
    if db is not None:
        yield db
        return
    with SessionLocal() as session:
        with session.begin():
            yield session


def _json_load(path: Path) -> dict:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {path.name}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Expected a valid UTF-8 JSON file") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Expected a JSON object containing dataset records")
    return payload


def _records(payload: dict, key: str, schema, required: tuple[str, ...]) -> list[dict]:
    items = payload.get(key)
    if not isinstance(items, list):
        raise HTTPException(status_code=422, detail=f"{key} must be an array")
    result, seen = [], set()
    for index, item in enumerate(items):
        if not isinstance(item, dict) or any(not isinstance(item.get(field), str) or not item[field].strip() for field in required):
            raise HTTPException(status_code=422, detail=f"{key}[{index}]: required fields: {', '.join(required)}")
        identity = tuple(item[field] for field in required[:2 if key == "role_profiles" else 1])
        if identity in seen:
            raise HTTPException(status_code=422, detail=f"{key}[{index}]: duplicate identifier")
        seen.add(identity)
        try:
            record = schema.model_validate(item).model_dump()
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=f"{key}[{index}]: invalid field values") from exc
        result.append(record)
    return result


def _upsert(db: Session, model, identity, data: dict) -> None:
    record = db.get(model, identity)
    if record is None:
        db.add(model(**data))
    else:
        for key, value in data.items():
            setattr(record, key, value)


def import_dataset_from_path(dataset_dir: str | None = None) -> dict[str, Any]:
    resolved_dir = Path(dataset_dir or settings.dataset_dir)
    if not resolved_dir.is_dir():
        raise HTTPException(status_code=404, detail="Dataset directory not found")
    with import_transaction() as db:
        return {
            "employees": import_employees(resolved_dir / "employees.json", db),
            "events": import_events(resolved_dir / "events.json", db),
            "skills": import_skills(resolved_dir / "skills.json", db),
            "history": import_history(resolved_dir / "activity_history.csv", db),
        }


def seed_demo_data() -> dict[str, Any]:
    with SessionLocal() as db:
        if db.query(Employee).first() is not None:
            return {"status": "already_seeded", "employees": db.query(Employee).count()}
    return import_dataset_from_path(str(settings.dataset_path))


def import_employees(file_path: str | Path, db: Session | None = None) -> int:
    employees = _records(_json_load(Path(file_path)), "employees", EmployeeBase, ("employee_id", "full_name"))
    with import_transaction(db) as session:
        for item in employees:
            _upsert(session, Employee, item["employee_id"], item)
        session.flush()
    return len(employees)


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


def import_events(file_path: str | Path, db: Session | None = None) -> int:
    events = _records(_json_load(Path(file_path)), "events", EventBase, ("event_id", "title"))
    with import_transaction(db) as session:
        for item in events:
            _upsert(session, Event, item["event_id"], item)
        session.flush()
    return len(events)


def import_skills(file_path: str | Path, db: Session | None = None) -> int:
    payload = _json_load(Path(file_path))
    skills = _records(payload, "skills", SkillBase, ("skill_id", "name", "type"))
    profiles = _records({"role_profiles": payload.get("role_profiles", [])}, "role_profiles", RoleProfileRead, ("role", "grade"))
    with import_transaction(db) as session:
        for item in skills:
            _upsert(session, Skill, item["skill_id"], item)
        for item in profiles:
            item.pop("id", None)
            profile = session.query(RoleProfile).filter_by(role=item["role"], grade=item["grade"]).first()
            if profile is None:
                session.add(RoleProfile(**item))
            else:
                for key, value in item.items():
                    setattr(profile, key, value)
        session.flush()
    return len(skills) + len(profiles)


def import_history(file_path: str | Path, db: Session | None = None) -> int:
    path = Path(file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {path.name}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if not {"record_id", "employee_id", "event_id"}.issubset(reader.fieldnames or []):
                raise HTTPException(status_code=422, detail="CSV requires record_id, employee_id and event_id columns")
            rows = []
            for row in reader:
                if None in row:
                    raise HTTPException(status_code=422, detail="CSV row contains too many columns")
                rows.append({key: value if value != "" else None for key, value in row.items()})
    except (UnicodeError, csv.Error) as exc:
        raise HTTPException(status_code=422, detail="Expected a valid UTF-8 CSV file") from exc
    history = _records({"history": rows}, "history", ActivityHistoryBase, ("record_id", "employee_id", "event_id"))
    with import_transaction(db) as session:
        employee_ids = {row[0] for row in session.query(Employee.employee_id).all()}
        event_ids = {row[0] for row in session.query(Event.event_id).all()}
        if any(item["employee_id"] not in employee_ids or item["event_id"] not in event_ids for item in history):
            raise HTTPException(status_code=422, detail="History references unknown employees or events; import them first")
        for item in history:
            _upsert(session, ActivityHistory, item["record_id"], item)
        session.flush()
    return len(history)
