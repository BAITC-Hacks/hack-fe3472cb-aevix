import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, RoleProfile, Skill
from app.utils.explainability import build_explanation, build_game_message
from app.utils.grade import GRADE_ORDER, get_role_target, grade_index, next_grade
from app.utils.scoring import clamp, derive_priority, expected_after, role_grade_relevance_score


def _load_skill_map() -> dict[str, str]:
    skill_map = {}
    db: Session = SessionLocal()
    try:
        rows = db.query(Skill).all()
        for row in rows:
            skill_map[row.skill_id] = row.name
    finally:
        db.close()
    return skill_map


def _calculate_progress(employee: Employee, target_role: str, target_grade: str) -> float:
    db: Session = SessionLocal()
    try:
        profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
    finally:
        db.close()
    if not profile:
        return 100.0

    required_skills = profile.required_skills or {}
    critical = set(profile.critical_skills or [])
    weighted_values = []
    for skill_id, required_level in required_skills.items():
        current_level = int((employee.skills or {}).get(skill_id, 0))
        progress = min(current_level / max(required_level, 1), 1.0)
        weight = 1.5 if skill_id in critical else 1.0
        weighted_values.append(progress * weight)

    if not weighted_values:
        return 100.0
    return round(sum(weighted_values) / sum([1.5 if skill_id in critical else 1.0 for skill_id in required_skills.keys()]) * 100, 2)


def get_employee_profile(employee_id: str) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        target_role, target_grade = get_role_target(employee.__dict__, employee.role)
        target_role = target_role or employee.role
        target_grade = target_grade or employee.grade or "Junior"
        profile = {
            "employee_id": employee.employee_id,
            "full_name": employee.full_name,
            "department": employee.department,
            "role": employee.role,
            "grade": employee.grade,
            "manager_id": employee.manager_id,
            "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
            "tenure_months": employee.tenure_months,
            "work_format": employee.work_format,
            "preferred_language": employee.preferred_language,
            "career_goal": employee.career_goal,
            "skills": employee.skills or {},
            "last_review_date": employee.last_review_date.isoformat() if employee.last_review_date else None,
            "target_role": target_role,
            "target_grade": target_grade,
            "progress_to_next_grade": _calculate_progress(employee, target_role, target_grade),
        }
        return profile
    finally:
        db.close()


def get_employee_recommendations(employee_id: str, limit: int = 3) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        target_role, target_grade = get_role_target(employee.__dict__, employee.role)
        target_role = target_role or employee.role
        target_grade = target_grade or employee.grade or "Junior"

        profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
        if not profile:
            return {
                "employee_id": employee.employee_id,
                "role": employee.role,
                "current_grade": employee.grade,
                "target_role": target_role,
                "target_grade": target_grade,
                "progress_to_next_grade": 100.0,
                "recommendations": [],
            }

        skill_names = _load_skill_map()
        required_skills = profile.required_skills or {}
        critical_skills = set(profile.critical_skills or [])
        current_skills = employee.skills or {}
        all_events = db.query(Event).filter(Event.mandatory.is_(False)).all()

        history_by_event = defaultdict(list)
        for entry in db.query(ActivityHistory).filter_by(employee_id=employee_id).all():
            history_by_event[entry.event_id].append(entry)

        recommendations = []
        for event in all_events:
            if not event.develops_skills:
                continue
            if event.target_roles and target_role not in event.target_roles and not any(role in event.target_roles for role in [employee.role, target_role]):
                continue
            if event.target_grades and target_grade not in event.target_grades and employee.grade not in event.target_grades:
                continue

            event_fit = []
            for skill_gain in event.develops_skills:
                skill_id = skill_gain.get("skill_id")
                if not skill_id:
                    continue
                if skill_id not in required_skills:
                    continue

                current_level = int(current_skills.get(skill_id, 0))
                required_level = int(required_skills[skill_id])
                gap = max(required_level - current_level, 0)
                if gap <= 0:
                    continue

                prereq_level = (event.prerequisites or {}).get(skill_id)
                if prereq_level and current_level < int(prereq_level):
                    continue

                expected = min(current_level + int(skill_gain.get("gain", 0)), int(skill_gain.get("max_level", current_level)))
                event_fit.append({
                    "skill_id": skill_id,
                    "skill_name": skill_names.get(skill_id, skill_id),
                    "current_level": current_level,
                    "required_level": required_level,
                    "gain": int(skill_gain.get("gain", 0)),
                    "max_level": int(skill_gain.get("max_level", 5)),
                    "expected_after": expected,
                    "gap_before": gap,
                    "gap_after": max(required_level - expected, 0),
                    "critical": skill_id in critical_skills,
                })

            if not event_fit:
                continue

            history_score = 0.0
            for old in history_by_event.get(event.event_id, []):
                if old.status == "completed":
                    history_score += 0.15
                elif old.status in {"declined", "dropped", "missed"}:
                    history_score -= 0.12

            gap_importance = sum(item["gap_before"] for item in event_fit) / max(len(event_fit), 1)
            critical_bonus = sum(1.5 if item["critical"] else 0.8 for item in event_fit)
            event_impact = sum(min(item["gain"] / max(item["max_level"], 1), 1.0) + (max(0, item["gap_before"] - item["gap_after"]) / max(item["required_level"], 1)) for item in event_fit)
            role_grade_relevance = role_grade_relevance_score(
                event.target_roles,
                event.target_grades,
                employee.role,
                target_role,
                target_grade,
            )
            score = (
                (gap_importance / 5.0) * 0.35
                + (critical_bonus / max(len(event_fit), 1)) * 0.20
                + (min(event_impact, 3.0) / 3.0) * 0.20
                + role_grade_relevance * 0.15
                + clamp(history_score + 0.4, 0.0, 1.0) * 0.10
            )

            if any(history.status == "completed" and history.event_id == event.event_id for history in history_by_event.get(event.event_id, [])):
                continue

            summary = event_fit[0]
            history_text = "Historia de participación sugiere una buena afinidad con este tipo de actividad." if history_score >= 0 else "La historia previa muestra que este tipo de evento necesita mayor validación antes de recomendarlo."
            reason = build_explanation(
                event.title,
                summary["skill_name"],
                summary["current_level"],
                summary["required_level"],
                summary["gain"],
                summary["expected_after"],
                history_text,
                target_grade,
            )
            recommendations.append({
                "event_id": event.event_id,
                "quest_title": event.title,
                "quest_type": event.type,
                "format": event.format,
                "duration_hours": event.duration_hours,
                "score": round(clamp(score), 2),
                "priority": derive_priority(clamp(score)),
                "affected_skills": [
                    {
                        "skill_id": item["skill_id"],
                        "skill_name": item["skill_name"],
                        "current_level": item["current_level"],
                        "required_level": item["required_level"],
                        "gain": item["gain"],
                        "max_level": item["max_level"],
                        "expected_after": item["expected_after"],
                        "gap_before": item["gap_before"],
                        "gap_after": item["gap_after"],
                    }
                    for item in event_fit
                ],
                "reason": reason,
                "game_message": build_game_message(event.title, target_grade, target_role),
            })

        recommendations.sort(key=lambda item: item["score"], reverse=True)
        response = {
            "employee_id": employee.employee_id,
            "role": employee.role,
            "current_grade": employee.grade,
            "target_role": target_role,
            "target_grade": target_grade,
            "progress_to_next_grade": _calculate_progress(employee, target_role, target_grade),
            "recommendations": recommendations[:limit],
        }
        return response
    finally:
        db.close()


def get_employee_trajectory(employee_id: str) -> list[dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        rows = db.query(ActivityHistory).filter_by(employee_id=employee_id).order_by(ActivityHistory.date.asc()).all()
        return [{
            "record_id": row.record_id,
            "event_id": row.event_id,
            "status": row.status,
            "date": row.date.isoformat() if row.date else None,
            "completion_pct": row.completion_pct,
            "score": row.score,
        } for row in rows]
    finally:
        db.close()


def complete_quest(employee_id: str, event_id: str) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        event = db.get(Event, event_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        progress_before = _calculate_progress(employee, (employee.career_goal or {}).get("target_role") or employee.role, (employee.career_goal or {}).get("target_grade") or next_grade(employee.grade or "Junior"))
        record_id = f"R_{employee_id}_{event_id}_{len(db.query(ActivityHistory).filter_by(employee_id=employee_id).all()) + 1}"
        db.add(ActivityHistory(
            record_id=record_id,
            employee_id=employee_id,
            event_id=event_id,
            date=date.today(),
            status="completed",
            completion_pct=100,
            score=100,
            assigned_by="self",
        ))

        target_profile = db.query(RoleProfile).filter_by(role=(employee.career_goal or {}).get("target_role") or employee.role, grade=(employee.career_goal or {}).get("target_grade") or next_grade(employee.grade or "Junior")).first()
        required_skills = (target_profile.required_skills if target_profile else None) or {}

        before_after = {}
        # копия словаря: иначе SQLAlchemy не заметит изменения JSON-поля и не сохранит их
        skills = dict(employee.skills or {})
        for item in event.develops_skills or []:
            skill_id = item.get("skill_id")
            before = int(skills.get(skill_id, 0))
            after = max(before, min(before + int(item.get("gain", 0)), int(item.get("max_level", 5))))
            skills[skill_id] = after
            before_after[skill_id] = {"before": before, "after": after, "required_for_next_grade": max(1, int(required_skills.get(skill_id, 1)))}
        employee.skills = skills

        db.commit()
        db.refresh(employee)
        progress_after = _calculate_progress(employee, (employee.career_goal or {}).get("target_role") or employee.role, (employee.career_goal or {}).get("target_grade") or next_grade(employee.grade or "Junior"))
        return {
            "employee_id": employee_id,
            "completed_quest": event.title,
            "updated_skills": before_after,
            "progress_to_next_grade_before": round(progress_before, 2),
            "progress_to_next_grade_after": round(progress_after, 2),
            "message": f"Квест завершён. {event.title} отмечен как выполненный.",
        }
    finally:
        db.close()
