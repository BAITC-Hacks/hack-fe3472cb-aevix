from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, QuestProgress, RoleProfile, Wallet
from app.services.recommendation_service import get_employee_recommendations
from app.utils.grade import get_role_target, grade_index


CITY_MAX_LEVEL = 10
CITY_COURSES_PER_LEVEL = 2


def _completed_quest_ids(db: Session, employee_id: str) -> set[str]:
    return {
        event_id
        for (event_id,) in db.query(ActivityHistory.event_id)
        .filter_by(employee_id=employee_id, status="completed")
        .distinct()
        .all()
    }


def _city_progress(completed_courses: int) -> dict[str, int]:
    """City growth follows distinct learning completions, independently of grade."""
    level = min(CITY_MAX_LEVEL, 1 + completed_courses // CITY_COURSES_PER_LEVEL)
    at_max_level = level == CITY_MAX_LEVEL
    current_level_courses = completed_courses % CITY_COURSES_PER_LEVEL
    return {
        "level": level,
        "max_level": CITY_MAX_LEVEL,
        "completed_courses": completed_courses,
        "courses_per_level": CITY_COURSES_PER_LEVEL,
        "courses_to_next_level": 0 if at_max_level else CITY_COURSES_PER_LEVEL - current_level_courses,
        "progress_to_next_level": 100 if at_max_level else current_level_courses * 100 // CITY_COURSES_PER_LEVEL,
    }


def get_game_map(employee_id: str) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        recs = get_employee_recommendations(employee_id)
        target_role, target_grade = get_role_target(employee.__dict__, employee.role)
        profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
        required = (profile.required_skills if profile else None) or {}
        current = employee.skills or {}
        wallet = db.get(Wallet, employee_id)
        completed = {
            item.event_id
            for item in db.query(ActivityHistory).filter_by(employee_id=employee_id, status="completed").all()
        }
        selected = db.query(QuestProgress).filter_by(employee_id=employee_id).all()
        groups = [
            ("engineering", "Engineering District", ["SK_SYSTEM_DESIGN", "SK_API_DESIGN", "SK_PYTHON"], ["Governance"]),
            ("security", "Security Gate", ["SK_APP_SECURITY"], ["Governance"]),
            ("communication", "Communication Bridge", ["SK_COMMUNICATION", "SK_PUBLIC_SPEAKING"], ["Social"]),
            ("leadership", "Leadership Tower", ["SK_LEADERSHIP", "SK_MENTORING"], ["Social", "Governance"]),
        ]
        districts = []
        for district_id, name, skill_ids, impact_tags in groups:
            ratios = [
                min(int(current.get(skill_id, 0)) / max(int(required.get(skill_id, 1)), 1), 1.0)
                for skill_id in skill_ids
                if skill_id in required
            ]
            progress = round(sum(ratios) / len(ratios) * 100) if ratios else 0
            event_ids = [
                item["event_id"]
                for item in recs["recommendations"]
                if any(skill["skill_id"] in skill_ids for skill in item["affected_skills"])
            ]
            districts.append({
                "id": district_id,
                "name": name,
                "progress": progress,
                "status": "active" if progress > 0 or event_ids else "locked",
                "related_skills": skill_ids,
                "impact_tags": impact_tags,
                "recommended_event_ids": event_ids,
            })
        nodes = [
            {"id": "profile", "title": "Current Profile", "status": "completed"},
            {"id": "core_skills", "title": "Core Skills", "status": "completed" if recs["progress_to_next_grade"] >= 100 else "active"},
            {"id": "next_grade", "title": f"{target_grade} Ready", "status": "active" if recs["progress_to_next_grade"] >= 100 else "locked"},
        ]
        return {
            "employee_id": employee_id,
            "city_name": "Career City",
            "center": {
                "name": "Halyk Bank Tower",
                "level": grade_index(employee.grade) + 1,
                "city_level": city_progress["level"],
                "wallet_balance": wallet.balance if wallet else 0,
                "progress_to_next_grade": recs["progress_to_next_grade"],
            },
            "districts": districts,
            "quest_board": [
                {
                    "event_id": item["event_id"],
                    "title": item.get("title", item.get("quest_title")),
                    "source": "recommendation_engine",
                    "score": item["score"],
                }
                for item in recs["recommendations"]
            ],
            "current_zone": employee.grade,
            "target_zone": target_grade,
            "career_level": grade_index(employee.grade) + 1,
            "city_level": city_progress["level"],
            "city_progress": city_progress,
            "progress_to_next_grade": recs["progress_to_next_grade"],
            "nodes": nodes,
            "recommended_quest_ids": [item["event_id"] for item in recs["recommendations"]],
            "completed_quest_ids": sorted(completed),
            "selected_quests": [
                {"event_id": item.event_id, "status": item.status, "mode": item.mode}
                for item in selected
                if item.status != "completed"
            ],
        }
    finally:
        db.close()


def get_game_progress(employee_id: str) -> dict[str, Any]:
    recs = get_employee_recommendations(employee_id)
    with SessionLocal() as db:
        city_progress = _city_progress(len(_completed_quest_ids(db, employee_id)))
    return {
        "employee_id": employee_id,
        "progress_to_next_grade": recs["progress_to_next_grade"],
        "recommendations": recs["recommendations"],
        "city_level": city_progress["level"],
        "city_progress": city_progress,
    }


def get_game_quests(employee_id: str) -> list[dict[str, Any]]:
    recs = get_employee_recommendations(employee_id)
    return [{"event_id": item["event_id"], "title": item["quest_title"], "priority": item["priority"], "score": item["score"]} for item in recs["recommendations"]]
