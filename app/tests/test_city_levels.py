"""The ten city illustrations follow persisted learning, not career grade."""
from datetime import date

import pytest

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee
from app.services.game_service import get_game_map, get_game_progress
from app.services.recommendation_service import complete_quest
from app.utils.grade import grade_index


@pytest.mark.parametrize(
    "completed,level,remaining,progress",
    [
        (0, 1, 2, 0), (1, 1, 1, 50),
        (2, 2, 2, 0), (3, 2, 1, 50),
        (4, 3, 2, 0), (5, 3, 1, 50),
        (6, 4, 2, 0), (7, 4, 1, 50),
        (8, 5, 2, 0), (9, 5, 1, 50),
        (10, 6, 2, 0), (11, 6, 1, 50),
        (12, 7, 2, 0), (13, 7, 1, 50),
        (14, 8, 2, 0), (15, 8, 1, 50),
        (16, 9, 2, 0), (17, 9, 1, 50),
        (18, 10, 0, 100), (19, 10, 0, 100),
        (20, 10, 0, 100), (40, 10, 0, 100),
    ],
)
def test_every_city_level_boundary(completed, level, remaining, progress):
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002").delete()
        db.add_all([
            ActivityHistory(
                record_id=f"CITY_{index}", employee_id="E0002",
                event_id=f"CITY_EVENT_{index}", status="completed", completion_pct=100,
            )
            for index in range(completed)
        ])
        career_level = grade_index(db.get(Employee, "E0002").grade) + 1
        db.commit()

    city = get_game_map("E0002")
    expected = {
        "level": level,
        "max_level": 10,
        "completed_courses": completed,
        "courses_per_level": 2,
        "courses_to_next_level": remaining,
        "progress_to_next_level": progress,
    }
    assert city["city_progress"] == expected
    assert city["city_level"] == city["center"]["city_level"] == level
    assert city["career_level"] == city["center"]["level"] == career_level
    assert len(city["completed_quest_ids"]) == completed
    summary = get_game_progress("E0002")
    assert summary["city_progress"] == expected
    assert summary["city_level"] == level


def test_city_counts_distinct_completed_events_for_selected_employee_only():
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002").delete()
        for index, status in enumerate([
            "completed", "completed", "in_progress", "overdue", "declined", "dropped", "registered",
        ]):
            db.add(ActivityHistory(
                record_id=f"CITY_STATUS_{index}", employee_id="E0002",
                event_id="EV_005" if status == "completed" else f"OTHER_{index}",
                status=status, completion_pct=100,
            ))
        db.add(ActivityHistory(
            record_id="CITY_OTHER_EMPLOYEE", employee_id="E0001",
            event_id="EV_002", status="completed", completion_pct=100,
        ))
        db.commit()

    city = get_game_map("E0002")
    assert city["completed_quest_ids"] == ["EV_005"]
    assert city["city_progress"]["completed_courses"] == 1
    assert city["city_progress"]["progress_to_next_level"] == 50
    assert city["city_level"] == 1


def test_completing_second_course_persists_next_city_level():
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002").delete()
        db.add_all([
            ActivityHistory(record_id="CITY_FIRST", employee_id="E0002", event_id="EV_001", status="completed", completion_pct=100),
            ActivityHistory(record_id="CITY_NEXT", employee_id="E0002", event_id="EV_005", status="in_progress", completion_pct=25),
        ])
        db.commit()
    before = get_game_map("E0002")
    assert before["city_level"] == 1
    assert before["city_progress"]["courses_to_next_level"] == 1

    complete_quest("E0002", "EV_005")

    after = get_game_map("E0002")
    assert after["city_level"] == 2
    assert after["city_progress"]["completed_courses"] == 2
    assert after["city_progress"]["progress_to_next_level"] == 0
    assert after["career_level"] == before["career_level"]
    assert get_game_progress("E0002")["city_progress"] == after["city_progress"]


def test_repeating_club_does_not_advance_city_twice():
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002").delete()
        db.add(ActivityHistory(
            record_id="CITY_OLD_CLUB", employee_id="E0002", event_id="EV_036",
            status="completed", completion_pct=100, date=date(2025, 1, 1),
        ))
        db.commit()
    before = get_game_map("E0002")

    complete_quest("E0002", "EV_036")

    assert get_game_map("E0002")["city_progress"] == before["city_progress"]
