from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, RoleProfile, Skill
from app.services.progress_service import compute_progress_to_next_grade
from app.services.recommendation_service import complete_quest, get_employee_profile, get_employee_recommendations, get_employee_trajectory

router = APIRouter()


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
def employee_recommendations(employee_id: str) -> dict[str, Any]:
    return get_employee_recommendations(employee_id)


@router.post("/{employee_id}/quests/{event_id}/complete")
def complete_employee_quest(employee_id: str, event_id: str) -> dict[str, Any]:
    return complete_quest(employee_id, event_id)
