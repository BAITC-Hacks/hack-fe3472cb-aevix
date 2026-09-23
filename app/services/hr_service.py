from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, RoleProfile, Skill
from app.utils.grade import get_role_target
from app.services.progress_service import compute_progress_to_next_grade


def get_hr_dashboard() -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employees = db.query(Employee).all()
        total_employees = len(employees)
        avg_progress = sum(compute_progress_to_next_grade(emp) for emp in employees) / total_employees if total_employees else 0.0
        gap_counter = defaultdict(lambda: {"count": 0, "total_gap": 0.0})
        inactive = 0
        risky = set()
        for emp in employees:
            target_role, target_grade = get_role_target(emp.__dict__, emp.role)
            profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
            for skill_id, required in (profile.required_skills if profile else {}).items():
                gap = max(0, int(required) - int((emp.skills or {}).get(skill_id, 0)))
                if gap:
                    gap_counter[skill_id]["count"] += 1
                    gap_counter[skill_id]["total_gap"] += gap
            history = db.query(ActivityHistory).filter_by(employee_id=emp.employee_id).all()
            if not history or all(item.status in {"declined", "missed", "no_show", "overdue", "dropped"} for item in history):
                inactive += 1
                if emp.grade:
                    risky.add(emp.grade)

        top_skill_gaps = []
        for skill_id, values in sorted(gap_counter.items(), key=lambda item: item[1]["count"], reverse=True)[:5]:
            skill = db.get(Skill, skill_id)
            skill_name = skill.name if skill else skill_id
            top_skill_gaps.append({
                "skill_id": skill_id,
                "skill_name": skill_name,
                "affected_employees": values["count"],
                "average_gap": round(values["total_gap"] / max(values["count"], 1), 2),
            })

        activity = db.query(ActivityHistory).all()
        completion_rate = round(sum(row.status == "completed" for row in activity) / len(activity), 2) if activity else 0.0

        popular = Counter(row.event_id for row in db.query(ActivityHistory).all())
        popular_events = [{"event_id": event_id, "count": count} for event_id, count in popular.most_common(5)]
        risky_segments = sorted(risky)

        return {
            "total_employees": total_employees,
            "average_progress_to_next_grade": round(avg_progress, 2),
            "top_skill_gaps": top_skill_gaps,
            "inactive_employees_count": inactive,
            "events_completion_rate": completion_rate,
            "popular_events": popular_events,
            "risky_segments": risky_segments,
        }
    finally:
        db.close()
