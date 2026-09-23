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
    if not employee:
        return default_role, next_grade(default_role and next_grade(default_role))

    goal = employee.get("career_goal") or {}
    if goal and goal.get("target_role"):
        target_role = goal["target_role"]
        target_grade = goal.get("target_grade") or next_grade(employee.get("grade"))
        return target_role, target_grade

    role = employee.get("role") or default_role
    current_grade = employee.get("grade") or "Junior"
    target_grade = next_grade(current_grade)
    return role, target_grade
