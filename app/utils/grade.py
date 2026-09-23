GRADE_ORDER = ["Junior", "Middle", "Senior", "Lead"]


def grade_index(grade: str | None) -> int:
    if not grade:
        return 0
    try:
        return GRADE_ORDER.index(grade)
    except ValueError:
        return 0


def next_grade(grade: str | None) -> str | None:
    idx = grade_index(grade)
    if idx < len(GRADE_ORDER) - 1:
        return GRADE_ORDER[idx + 1]
    return grade if grade == "Lead" else "Lead"


def get_role_target(employee: dict | None, default_role: str | None = None) -> tuple[str | None, str | None]:
    employee = employee or {}
    goal = employee.get("career_goal") or {}
    role = goal.get("target_role") or employee.get("role") or default_role
    current_grade = employee.get("grade") or "Junior"
    target_grade = goal.get("target_grade") or next_grade(current_grade)
    return role, target_grade
