from collections import defaultdict
from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, CoinTransaction, Employee, Event, QuestPlan, QuestProgress, RoleProfile, Skill, Wallet
from app.services.llm_service import explain_recommendations
from app.services.quest_service import (
    ACTIVE_HISTORY_STATUSES, RECURRING_EVENTS, _has_completed, _quest_records,
    mark_quest_completed, quest_prerequisites_met, quest_step_counts, quest_write_transaction,
    require_completed_quest_steps,
)
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


def _calculate_progress(employee: Employee, target_role: str, target_grade: str, db: Session | None = None) -> float:
    if db is None:
        with SessionLocal() as session:
            return _calculate_progress(employee, target_role, target_grade, session)
    profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
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


def get_employee_recommendations(employee_id: str, limit: int = 3, use_llm: bool = True, language: str = "ru") -> dict[str, Any]:
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
                "explanation_provider": "template",
                "explanation_summary": "No target role profile is available for recommendations.",
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
            if not quest_prerequisites_met(employee, event):
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
            if already_completed:
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
            scoring_factors = {
                "skill_gap_score": round(skill_gap_score, 2),
                "critical_skill_score": round(critical_skill_score, 2),
                "event_impact_score": round(event_impact_score, 2),
                "role_grade_relevance_score": round(role_grade_relevance, 2),
                "history_score": round(history_score, 2),
                "prerequisite_score": round(prerequisite_score, 2),
            }

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
                "description": event.description,
                "event_id": event.event_id,
                "type": event.type,
                "quest_title": event.title,
                "quest_type": event.type,
                "format": event.format,
                "duration_hours": event.duration_hours,
                "score": round(clamp(score), 2),
                "priority": derive_priority(clamp(score)),
                "scoring_factors": scoring_factors,
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
        recommendations = recommendations[:limit]
        llm_result = explain_recommendations(
            {
                "role": employee.role,
                "current_grade": employee.grade,
                "target_role": target_role,
                "target_grade": target_grade,
                "progress_to_next_grade": _calculate_progress(employee, target_role, target_grade),
                "language": language,
            },
            recommendations,
        ) if use_llm else {
            "provider": "template",
            "summary": "Recommendations were calculated by the deterministic Career Quest engine.",
            "recommendation_explanations": [],
        }
        explanations = {item["event_id"]: item for item in llm_result["recommendation_explanations"]}
        for recommendation in recommendations:
            generated = explanations.get(recommendation["event_id"])
            if generated:
                recommendation["agent_explanation"] = generated["explanation"]
                recommendation["employee_friendly_reason"] = generated["employee_friendly_reason"]
                recommendation["risk_note"] = generated["risk_note"]
                recommendation["expected_outcome"] = generated["expected_outcome"]
        response = {
            "employee_id": employee.employee_id,
            "role": employee.role,
            "current_grade": employee.grade,
            "target_role": target_role,
            "target_grade": target_grade,
            "progress_to_next_grade": _calculate_progress(employee, target_role, target_grade),
            "recommendations": recommendations,
            "explanation_provider": llm_result["provider"],
            "explanation_summary": llm_result["summary"],
        }
        return response
    finally:
        db.close()


def get_employee_trajectory(employee_id: str) -> list[dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        if db.get(Employee, employee_id) is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        rows = db.query(ActivityHistory).filter_by(employee_id=employee_id).order_by(ActivityHistory.date.asc()).all()
        progress_rows = db.query(QuestProgress).filter_by(employee_id=employee_id).all()
        progress_by_event = {row.event_id: row for row in progress_rows}
        event_ids = {row.event_id for row in rows} | set(progress_by_event)
        events = {row.event_id: row for row in db.query(Event).filter(Event.event_id.in_(event_ids)).all()}
        counts = {event_id: quest_step_counts(db, employee_id, event_id) for event_id in event_ids}

        def details(event_id: str) -> dict[str, Any]:
            completed, total = counts[event_id]
            event = events.get(event_id)
            return {
                "title": event.title if event else event_id,
                "completed_steps": completed, "total_steps": total,
                "mode": progress_by_event[event_id].mode if event_id in progress_by_event else "solo",
            }

        history = [{
            "source": "activity_history", "record_id": row.record_id, "event_id": row.event_id,
            "status": row.status, "date": row.date.isoformat() if row.date else None,
            "completion_pct": row.completion_pct, "score": row.score, **details(row.event_id),
        } for row in rows]
        for progress in progress_rows:
            completed, total = counts[progress.event_id]
            progress_date = progress.completed_at or progress.started_at
            history.append({
                "source": "quest_progress", "record_id": f"QUEST_{progress.id}",
                "event_id": progress.event_id, "status": progress.status,
                "date": progress_date.isoformat() if progress_date else None,
                "completion_pct": 100 if progress.status == "completed" else round(completed / total * 100) if total else 0,
                "score": None, **details(progress.event_id),
            })
        return history
    finally:
        db.close()


def complete_quest(employee_id: str, event_id: str) -> dict[str, Any]:
    with quest_write_transaction() as db:
        return _complete_quest(db, employee_id, event_id)


def _complete_quest(db: Session, employee_id: str, event_id: str) -> dict[str, Any]:
    employee, event, progress = _quest_records(db, employee_id, event_id)
    if _has_completed(db, employee_id, event_id, progress):
        completed_today = db.query(ActivityHistory).filter_by(
            employee_id=employee_id, event_id=event_id, status="completed", date=date.today(),
        ).first()
        # The recurring club supports later sessions while duplicate completion
        # requests for today's participation remain conflicts.
        fresh_selection = progress is not None and progress.status == "selected"
        if event_id not in RECURRING_EVENTS or (completed_today and not fresh_selection):
            raise HTTPException(status_code=409, detail="Quest already completed")
        if db.get(QuestPlan, (employee_id, event_id)) is not None and not fresh_selection:
            raise HTTPException(status_code=409, detail="Select the recurring quest to start a new participation")

    require_completed_quest_steps(db, employee_id, event_id)

    target_role, target_grade = get_role_target(employee.__dict__, employee.role)
    progress_before = _calculate_progress(employee, target_role, target_grade, db)
    active = db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).filter(
        ActivityHistory.status.in_(ACTIVE_HISTORY_STATUSES)
    ).all()
    if not active:
        active = [ActivityHistory(
            record_id=f"R_{uuid4().hex}", employee_id=employee_id, event_id=event_id, assigned_by="self",
        )]
        db.add(active[0])
    for entry in active:
        entry.date = date.today()
        entry.status = "completed"
        entry.completion_pct = 100
        entry.score = 100

    before_after = {}
    role_profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
    critical_skills = set(role_profile.critical_skills or []) if role_profile else set()
    required_skills = (role_profile.required_skills or {}) if role_profile else {}
    updated_skills = dict(employee.skills or {})
    for item in event.develops_skills or []:
        skill_id = item.get("skill_id")
        if not skill_id:
            continue
        before = int(updated_skills.get(skill_id, 0))
        after = expected_after(before, int(item.get("gain", 0)), int(item.get("max_level", 5)))
        updated_skills[skill_id] = after
        before_after[skill_id] = {
            "before": before, "after": after,
            "required_for_next_grade": int(required_skills.get(skill_id, 0)),
        }
    # Reassign JSON so SQLAlchemy persists changes even without MutableDict.
    employee.skills = updated_skills
    progress_after = _calculate_progress(employee, target_role, target_grade, db)
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
    wallet = db.query(Wallet).filter_by(employee_id=employee_id).with_for_update().first()
    if not event.mandatory:
        coins_earned = max(int((event.duration_hours or 0) * 10), 0)
        if improved_critical:
            coins_earned += 50
        if gap_reduced:
            coins_earned += 30
        coin_reason = "Voluntary quest completed"
        if improved_critical:
            coin_reason += ", critical skill improved"
        if gap_reduced:
            coin_reason += ", skill gap reduced"
        if wallet is None:
            wallet = Wallet(employee_id=employee_id, balance=0)
            db.add(wallet)
        wallet.balance += coins_earned
        db.add(CoinTransaction(
            transaction_id=f"TX_{uuid4().hex}", employee_id=employee_id, event_id=event_id,
            amount=coins_earned, reason=coin_reason, created_at=date.today(),
        ))
    mark_quest_completed(employee_id, event_id, db)
    db.flush()
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
