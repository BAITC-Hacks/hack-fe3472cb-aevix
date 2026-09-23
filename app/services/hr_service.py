from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, ESGContribution, RoleProfile, Skill, Team
from app.services.progress_service import compute_progress_to_next_grade
from app.services.recommendation_service import get_employee_recommendations
from app.utils.grade import get_role_target


def get_hr_dashboard() -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        employees = db.query(Employee).all()
        total_employees = len(employees)
        avg_progress = sum(compute_progress_to_next_grade(emp) for emp in employees) / total_employees if total_employees else 0.0
        gap_counter = defaultdict(lambda: {"count": 0, "total_gap": 0.0})
        profiles = {(profile.role, profile.grade): profile for profile in db.query(RoleProfile).all()}
        skill_names = {skill.skill_id: skill.name for skill in db.query(Skill).all()}
        activity = db.query(ActivityHistory).all()
        history_by_employee = defaultdict(list)
        for row in activity:
            history_by_employee[row.employee_id].append(row)
        inactive = 0
        risky = set()
        for emp in employees:
            target = get_role_target(emp.__dict__, emp.role)
            profile = profiles.get(target)
            for skill_id, required in ((profile.required_skills or {}) if profile else {}).items():
                gap = max(0, int(required) - int((emp.skills or {}).get(skill_id, 0)))
                if gap:
                    gap_counter[skill_id]["count"] += 1
                    gap_counter[skill_id]["total_gap"] += gap
            history = history_by_employee[emp.employee_id]
            if not history or all(item.status in {"declined", "missed", "no_show", "overdue", "dropped"} for item in history):
                inactive += 1
                if emp.grade:
                    risky.add(emp.grade)

        top_skill_gaps = []
        for skill_id, values in sorted(gap_counter.items(), key=lambda item: item[1]["count"], reverse=True)[:5]:
            skill_name = skill_names.get(skill_id, skill_id)
            top_skill_gaps.append({
                "skill_id": skill_id,
                "skill_name": skill_name,
                "affected_employees": values["count"],
                "average_gap": round(values["total_gap"] / max(values["count"], 1), 2),
            })

        completion_rate = round(sum(row.status == "completed" for row in activity) / len(activity), 2) if activity else 0.0

        popular = Counter(row.event_id for row in activity)
        popular_events = [{"event_id": event_id, "count": count} for event_id, count in popular.most_common(5)]
        risky_segments = sorted(risky)
        participation_by_activity = [
            {"event_id": event_id, "participations": count}
            for event_id, count in popular.most_common()
        ]
        employees_without_recommendations = []
        for employee in employees:
            if not get_employee_recommendations(employee.employee_id, use_llm=False).get("recommendations"):
                employees_without_recommendations.append(employee.employee_id)
        esg_rows = db.query(ESGContribution).all()
        teams = db.query(Team).all()
        team_activity = {
            "teams_count": len(teams),
            "completed_team_quests": sum(team.completed_team_quests for team in teams),
        }

        return {
            "total_employees": total_employees,
            "average_progress_to_next_grade": round(avg_progress, 2),
            "top_skill_gaps": top_skill_gaps,
            "inactive_employees_count": inactive,
            "events_completion_rate": completion_rate,
            "popular_events": popular_events,
            "risky_segments": risky_segments,
            "employees_without_recommendations": employees_without_recommendations,
            "participation_by_activity": participation_by_activity,
            "esg_engagement": {
                "total_contributed_coins": sum(row.coins for row in esg_rows),
                "contributors_count": len({row.employee_id for row in esg_rows}),
            },
            "team_quest_activity": team_activity,
        }
    finally:
        db.close()
