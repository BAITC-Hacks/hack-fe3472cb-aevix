from __future__ import annotations

from typing import Any


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def expected_after(current_level: int, gain: int, max_level: int) -> int:
    return max(int(current_level), min(int(current_level) + max(int(gain), 0), int(max_level)))


def normalize_gap(value: float) -> float:
    return clamp(value / 5.0)


def role_grade_relevance_score(target_roles: list[str] | None, target_grades: list[str] | None, employee_role: str | None, employee_target_role: str | None, target_grade: str | None) -> float:
    if not target_roles:
        return 0.7

    role_match = 1.0 if employee_role in target_roles or employee_target_role in target_roles else 0.5
    grade_match = 1.0 if target_grade in (target_grades or []) else 0.6 if target_grades else 0.7
    return clamp((role_match * 0.7 + grade_match * 0.3))


def derive_priority(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"
