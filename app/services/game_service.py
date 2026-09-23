from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Employee, Event
from app.services.recommendation_service import get_employee_recommendations
from app.utils.grade import get_role_target


def get_game_map(employee_id: str) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise ValueError("Employee not found")
        target_role, target_grade = get_role_target(employee.__dict__, employee.role)
        recs = get_employee_recommendations(employee_id)
        nodes = [
            {"id": "profile", "title": "Current Profile", "status": "completed"},
            {"id": "core_skills", "title": "Core Skills", "status": "active"},
            {"id": "next_grade", "title": f"{target_grade} Ready", "status": "locked"},
        ]
        return {
            "employee_id": employee_id,
            "current_zone": employee.grade,
            "target_zone": target_grade,
            "career_level": 3,
            "progress_to_next_grade": recs["progress_to_next_grade"],
            "nodes": nodes,
            "recommended_quest_ids": [item["event_id"] for item in recs["recommendations"][:2]],
        }
    finally:
        db.close()


def get_game_progress(employee_id: str) -> dict[str, Any]:
    recs = get_employee_recommendations(employee_id)
    return {"employee_id": employee_id, "progress_to_next_grade": recs["progress_to_next_grade"], "recommendations": recs["recommendations"]}


def get_game_quests(employee_id: str) -> list[dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        recs = get_employee_recommendations(employee_id)
        return [{"event_id": item["event_id"], "title": item["quest_title"], "priority": item["priority"], "score": item["score"]} for item in recs["recommendations"]]
    finally:
        db.close()
