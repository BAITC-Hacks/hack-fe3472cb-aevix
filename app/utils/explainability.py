from typing import Any


def build_explanation(event_title: str, skill_name: str, current_level: int, required_level: int, gain: int, expected_after: int, history_text: str, target_grade: str) -> str:
    gap = required_level - current_level
    return (
        f"{event_title} focuses on {skill_name}, which is currently at {current_level} and required at {required_level} for {target_grade}. "
        f"This quest adds +{gain} to the skill and is expected to reach level {expected_after}, closing a gap of {gap}. "
        f"{history_text}"
    )


def build_game_message(event_title: str, target_grade: str, role: str) -> str:
    return f"Следующий квест на карте: {event_title}. Он приблизит тебя к уровню {target_grade} {role}."
