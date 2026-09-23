from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Employee, Event, RoleProfile, Skill
from app.schemas.employee import EmployeeBase, QuestSelection
from app.services.auth_service import require_hr
from app.services.import_service import register_employee
from app.services.quest_service import complete_quest_step, get_quest_steps, select_quest
from app.services.recommendation_service import complete_quest, get_employee_profile, get_employee_recommendations, get_employee_trajectory

router = APIRouter()


@router.post("/register", dependencies=[Depends(require_hr)])
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
        def serialize(row: Any) -> dict[str, Any]:
            return {column.name: getattr(row, column.name) for column in row.__table__.columns}

        return {
            "skills": [serialize(row) for row in db.query(Skill).order_by(Skill.skill_id).all()],
            "role_profiles": [serialize(row) for row in db.query(RoleProfile).order_by(RoleProfile.role, RoleProfile.grade).all()],
            "events": [serialize(row) for row in db.query(Event).order_by(Event.event_id).all()],
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
def employee_recommendations(
    employee_id: str,
    include_explanations: bool = False,
    language: str = Query(default="ru", pattern="^(ru|kk|en)$"),
    limit: int = Query(default=3, ge=1, le=100),
) -> dict[str, Any]:
    return get_employee_recommendations(employee_id, limit=limit, use_llm=include_explanations, language=language)


@router.post("/{employee_id}/quests/{event_id}/complete")
def complete_employee_quest(employee_id: str, event_id: str) -> dict[str, Any]:
    return complete_quest(employee_id, event_id)


@router.post("/{employee_id}/quests/{event_id}/select")
def select_employee_quest(employee_id: str, event_id: str, payload: QuestSelection | None = None) -> dict[str, Any]:
    return select_quest(employee_id, event_id, payload.mode if payload else "solo")


@router.get("/{employee_id}/quests/{event_id}/steps")
def quest_steps(
    employee_id: str, event_id: str,
    language: str | None = Query(default=None, pattern="^(ru|kk|en)$"),
) -> dict[str, Any]:
    return get_quest_steps(employee_id, event_id, language=language)


@router.post("/{employee_id}/quests/{event_id}/steps/{step_number}/complete")
def complete_step(employee_id: str, event_id: str, step_number: int) -> dict[str, Any]:
    return complete_quest_step(employee_id, event_id, step_number)
