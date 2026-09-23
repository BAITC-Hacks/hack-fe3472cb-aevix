from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Employee, RoleProfile
from app.db.database import SessionLocal
from app.utils.grade import get_role_target


def compute_progress_to_next_grade(employee: Employee, target_role: str | None = None, target_grade: str | None = None) -> float:
    db: Session = SessionLocal()
    try:
        if target_role is None or target_grade is None:
            target_role, target_grade = get_role_target(employee.__dict__, employee.role)
        profile = db.query(RoleProfile).filter_by(role=target_role, grade=target_grade).first()
        if not profile:
            return 100.0
        required_skills = profile.required_skills or {}
        if not required_skills:
            return 100.0
        weighted = []
        critical = set(profile.critical_skills or [])
        for skill_id, required_level in required_skills.items():
            current = int((employee.skills or {}).get(skill_id, 0))
            ratio = min(current / max(int(required_level), 1), 1.0)
            weight = 1.5 if skill_id in critical else 1.0
            weighted.append(ratio * weight)
        total_weight = sum(1.5 if skill_id in critical else 1.0 for skill_id in required_skills)
        return round((sum(weighted) / total_weight) * 100, 2)
    finally:
        db.close()
