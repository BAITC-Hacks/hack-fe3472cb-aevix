from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, RoleProfile
from app.services.progress_service import compute_progress_to_next_grade


def get_hr_dashboard() -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employees = db.query(Employee).all()
        total_employees = len(employees)
        avg_progress = sum(compute_progress_to_next_grade(emp) for emp in employees) / total_employees if total_employees else 0.0
        gap_counter = defaultdict(lambda: {"count": 0, "total_gap": 0.0})
        inactive = 0
        for emp in employees:
            if not emp.skills:
                continue
            for skill_id, current_level in (emp.skills or {}).items():
                found = False
                for profile in db.query(RoleProfile).all():
                    required = (profile.required_skills or {}).get(skill_id)
                    if required is not None and int(current_level) < int(required):
                        gap = int(required) - int(current_level)
                        gap_counter[skill_id]["count"] += 1
                        gap_counter[skill_id]["total_gap"] += gap
                        found = True
                        break
                if found:
                    continue
            history = db.query(ActivityHistory).filter_by(employee_id=emp.employee_id).all()
            if not history or all(item.status in {"declined", "missed", "dropped"} for item in history):
                inactive += 1

        top_skill_gaps = []
        for skill_id, values in sorted(gap_counter.items(), key=lambda item: item[1]["count"], reverse=True)[:5]:
            skill_name = skill_id
            top_skill_gaps.append({
                "skill_id": skill_id,
                "skill_name": skill_name,
                "affected_employees": values["count"],
                "average_gap": round(values["total_gap"] / max(values["count"], 1), 2),
            })

        events = db.query(Event).all()
        completion_rate = 0.0
        if events:
            completed = sum(1 for event in events if event.mandatory is False)
            completion_rate = round(completed / len(events), 2) if events else 0.0

        popular = Counter(row.event_id for row in db.query(ActivityHistory).all())
        popular_events = [{"event_id": event_id, "count": count} for event_id, count in popular.most_common(5)]
        risky_segments = ["Junior", "Middle"] if employees else []

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
