from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Employee, Event, RoleProfile, Skill
from app.schemas.employee import EmployeeBase
from app.services.import_service import register_employee
from app.services.quest_service import select_quest
from app.services.recommendation_service import complete_quest, get_employee_profile, get_employee_recommendations, get_employee_trajectory

router = APIRouter()


class QuestSelection(BaseModel):
    mode: Literal["solo", "team"] = "solo"


@router.post("/register")
def register(employee: EmployeeBase) -> dict[str, Any]:
    return register_employee(employee.model_dump())


@router.get("")
def list_employees() -> list[dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        rows = db.query(Employee).all()
        return [{
            "employee_id": row.employee_id,
            "full_name": row.full_name,
            "role": row.role,
            "grade": row.grade,
            "department": row.department,
            "target": row.career_goal,
        } for row in rows]
    finally:
        db.close()



@router.get("/catalog")
def catalog() -> dict[str, Any]:
    with SessionLocal() as db:
        return {
            "skills": [{"skill_id": row.skill_id, "name": row.name, "type": row.type, "category": row.category} for row in db.query(Skill).all()],
            "role_profiles": [{"role": row.role, "grade": row.grade, "required_skills": row.required_skills or {}, "critical_skills": row.critical_skills or []} for row in db.query(RoleProfile).all()],
            "events": [{"event_id": row.event_id, "title": row.title, "description": row.description, "type": row.type, "format": row.format, "duration_hours": row.duration_hours, "mandatory": row.mandatory, "upcoming_sessions": row.upcoming_sessions or []} for row in db.query(Event).all()],
        }

@router.get("/{employee_id}")
def get_employee(employee_id: str) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        row = db.get(Employee, employee_id)
        if not row:
            raise HTTPException(status_code=404, detail="Employee not found")
        return {
            "employee_id": row.employee_id,
            "full_name": row.full_name,
            "role": row.role,
            "grade": row.grade,
            "manager_id": row.manager_id,
            "skills": row.skills,
            "career_goal": row.career_goal,
        }
    finally:
        db.close()


@router.get("/{employee_id}/profile")
def employee_profile(employee_id: str) -> dict[str, Any]:
    return get_employee_profile(employee_id)


@router.get("/{employee_id}/trajectory")
def employee_trajectory(employee_id: str) -> list[dict[str, Any]]:
    return get_employee_trajectory(employee_id)


@router.get("/{employee_id}/recommendations")
def employee_recommendations(employee_id: str, include_explanations: bool = True, language: Literal["ru", "kk", "en"] = "en") -> dict[str, Any]:
    return get_employee_recommendations(employee_id, use_llm=include_explanations, language=language)


@router.post("/{employee_id}/quests/{event_id}/complete")
def complete_employee_quest(employee_id: str, event_id: str) -> dict[str, Any]:
    return complete_quest(employee_id, event_id)


@router.post("/{employee_id}/quests/{event_id}/select")
def select_employee_quest(employee_id: str, event_id: str, payload: QuestSelection | None = None) -> dict[str, Any]:
    return select_quest(employee_id, event_id, payload.mode if payload else "solo")
