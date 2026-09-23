from collections import defaultdict
from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, CoinTransaction, Employee, Event, RoleProfile, Skill, Wallet
from app.services.progress_service import compute_progress_to_next_grade as _calculate_progress
from app.utils.explainability import build_game_message
from app.utils.grade import get_role_target
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


def _completion_is_current(event: Event, history: list[ActivityHistory]) -> bool:
    """Allow a new club session or annual assignment, but not duplicate rewards."""
    completed = [entry for entry in history if entry.status == "completed"]
    if event.mandatory:
        return any(entry.date and entry.date.year == date.today().year for entry in completed)
    if event.event_id == "EV_036":
        return any(entry.date == date.today() for entry in completed)
    return bool(completed)


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
        events_by_id = {item.event_id: item for item in all_events}

        history_by_event = defaultdict(list)
        for entry in db.query(ActivityHistory).filter_by(employee_id=employee_id).all():
            history_by_event[entry.event_id].append(entry)
        all_history = [entry for entries in history_by_event.values() for entry in entries]

        recommendations = []
        for event in all_events:
            if not event.develops_skills:
                continue
            if event.target_roles and target_role not in event.target_roles and not any(role in event.target_roles for role in [employee.role, target_role]):
                continue
            if event.target_grades and target_grade not in event.target_grades and employee.grade not in event.target_grades:
                continue
            if any(int(current_skills.get(skill_id, 0)) < int(level) for skill_id, level in (event.prerequisites or {}).items()):
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

                expected = expected_after(current_level, int(skill_gain.get("gain", 0)), int(skill_gain.get("max_level", 5)))
                if expected <= current_level:
                    continue
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
                    "is_critical": skill_id in critical_skills,
                })

            if not event_fit:
                continue

            event_history = history_by_event.get(event.event_id, [])
            similar_history = [
                history_item for history_item in all_history
                if history_item.event_id == event.event_id
                or (events_by_id.get(history_item.event_id) and events_by_id[history_item.event_id].type == event.type)
            ]
            completed_similar = sum(item.status == "completed" for item in similar_history)
            missed_or_declined_similar = sum(item.status in {"missed", "no_show", "declined", "dropped"} for item in similar_history)
            already_completed = any(item.status == "completed" for item in event_history)
            if _completion_is_current(event, event_history):
                continue

            history_score = clamp(0.5 + completed_similar * 0.15 - missed_or_declined_similar * 0.5)
            skill_gap_score = clamp(sum(item["gap_before"] for item in event_fit) / max(len(event_fit) * 5, 1))
            critical_skill_score = sum(1.0 if item["is_critical"] else 0.0 for item in event_fit) / max(len(event_fit), 1)
            event_impact_score = clamp(sum(max(item["gap_before"] - item["gap_after"], 0) / max(item["required_level"], 1) for item in event_fit) / max(len(event_fit), 1))
            role_grade_relevance = role_grade_relevance_score(
                event.target_roles,
                event.target_grades,
                employee.role,
                target_role,
                target_grade,
            )
            prerequisite_score = 1.0 if not event.prerequisites else 0.8
            score = (
                skill_gap_score * 0.30
                + critical_skill_score * 0.20
                + event_impact_score * 0.20
                + role_grade_relevance * 0.15
                + history_score * 0.10
                + prerequisite_score * 0.05
            )

            why_recommended = [
                f"{item['skill_name']} is {item['current_level']}, required level for {target_grade} is {item['required_level']}"
                for item in event_fit
            ]
            for item in event_fit:
                if item["is_critical"]:
                    why_recommended.append("This is a critical skill for the target grade")
                why_recommended.append(f"The event improves {item['skill_name']} by +{item['gain']}")
            if completed_similar:
                why_recommended.append(f"The employee has completed similar activities before ({completed_similar})")
            if missed_or_declined_similar:
                why_recommended.append(f"Prior missed, declined, or dropped activities reduce priority ({missed_or_declined_similar})")
            summary = event_fit[0]
            explanation = (
                f"{summary['skill_name']} is currently {summary['current_level']} while {target_grade} {target_role} requires "
                f"{summary['required_level']}. The event improves {summary['skill_name']} by +{summary['gain']} and reduces "
                f"the gap from {summary['gap_before']} to {summary['gap_after']}. History contributes {history_score:.2f} "
                f"to the score ({completed_similar} completed similar, {missed_or_declined_similar} missed/declined/dropped)."
            )
            recommendations.append({
                "title": event.title,
                "event_id": event.event_id,
                "type": event.type,
                "quest_title": event.title,
                "quest_type": event.type,
                "format": event.format,
                "duration_hours": event.duration_hours,
                "score": round(clamp(score), 2),
                "priority": derive_priority(clamp(score)),
                "why_recommended": why_recommended,
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
                        "is_critical": item["is_critical"],
                    }
                    for item in event_fit
                ],
                "history_signal": {
                    "completed_similar": completed_similar,
                    "missed_or_declined_similar": missed_or_declined_similar,
                    "already_completed_this_event": already_completed,
                },
                "explanation": explanation,
                "reason": explanation,
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

        history = db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).all()
        if _completion_is_current(event, history):
            raise HTTPException(status_code=409, detail="Quest already completed")

        target_role, target_grade = get_role_target(employee.__dict__, employee.role)
        progress_before = _calculate_progress(employee, target_role, target_grade)
        active = [entry for entry in history if entry.status in {"in_progress", "overdue"}]
        if active:
            record_id = active[0].record_id
            for record in active:
                record.status = "completed"
                record.completion_pct = 100
                record.date = date.today()
                record.score = 100
        else:
            record_id = f"R_{uuid4().hex}"
            db.add(ActivityHistory(
                record_id=record_id, employee_id=employee_id, event_id=event_id,
                date=date.today(), status="completed", completion_pct=100, score=100, assigned_by="self",
            ))

        role_profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
        required_skills = (role_profile.required_skills if role_profile else None) or {}
        critical_skills = set(role_profile.critical_skills or []) if role_profile else set()

        before_after = {}
        # копия словаря: иначе SQLAlchemy не заметит изменения JSON-поля и не сохранит их
        skills = dict(employee.skills or {})
        for item in event.develops_skills or []:
            skill_id = item.get("skill_id")
            if not skill_id:
                continue
            before = int(skills.get(skill_id, 0))
            after = max(before, expected_after(before, int(item.get("gain", 0)), int(item.get("max_level", 5))))
            skills[skill_id] = after
            before_after[skill_id] = {
                "before": before,
                "after": after,
                "required_for_next_grade": max(1, int(required_skills.get(skill_id, 1))),
            }
        employee.skills = skills

        progress_after = _calculate_progress(employee, target_role, target_grade)
        improved_critical = any(
            skill_id in critical_skills and values["after"] > values["before"]
            for skill_id, values in before_after.items()
        )
        gap_reduced = any(
            values["after"] > values["before"] and values["before"] < values["required_for_next_grade"]
            for values in before_after.values()
        )
        coins_earned = 0
        coin_reason = "Mandatory event completed; no Growth Coins awarded"
        if not event.mandatory:
            coins_earned = int((event.duration_hours or 0) * 10)
            if improved_critical:
                coins_earned += 50
            if gap_reduced:
                coins_earned += 30
            coin_reason = "Voluntary quest completed"
            if improved_critical:
                coin_reason += ", critical skill improved"
            if gap_reduced:
                coin_reason += ", skill gap reduced"
            wallet = db.get(Wallet, employee_id)
            if wallet is None:
                wallet = Wallet(employee_id=employee_id, balance=0)
                db.add(wallet)
            wallet.balance += coins_earned
            db.add(CoinTransaction(
                transaction_id=f"TX_{employee_id}_{event_id}_{record_id}",
                employee_id=employee_id,
                event_id=event_id,
                amount=coins_earned,
                reason=coin_reason,
                created_at=date.today(),
            ))
        # History, skills and rewards must either all persist or all roll back.
        db.commit()
        wallet = db.get(Wallet, employee_id)
        return {
            "employee_id": employee_id,
            "completed_quest": event.title,
            "updated_skills": before_after,
            "progress_to_next_grade_before": round(progress_before, 2),
            "progress_to_next_grade_after": round(progress_after, 2),
            "coins_earned": coins_earned,
            "wallet_balance": wallet.balance if wallet else 0,
            "coin_reason": coin_reason,
            "message": f"Квест завершён. {event.title} отмечен как выполненный.",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
