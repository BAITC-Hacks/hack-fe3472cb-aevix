from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import event as sqlalchemy_event

from app.db.database import SessionLocal, init_db
from app.db.models import ActivityHistory, CoinTransaction, Employee, Event, RoleProfile, Wallet
from app.services.game_service import get_game_map
from app.services.import_service import seed_demo_data
from app.services.recommendation_service import complete_quest, get_employee_profile, get_employee_recommendations


def test_recommendation_service_targets_grade_gap():
    init_db()
    seed_demo_data()
    result = get_employee_recommendations("E0002")

    assert result["employee_id"] == "E0002"
    assert result["target_grade"] == "Senior"
    assert result["progress_to_next_grade"] >= 0
    assert len(result["recommendations"]) >= 1
    assert result["recommendations"][0]["score"] > 0


def test_recommendations_exclude_mandatory_and_explain_multiple_factors():
    result = get_employee_recommendations("E0002")

    assert all(item["event_id"] != "EV_001" for item in result["recommendations"])
    recommendation = result["recommendations"][0]
    assert recommendation["why_recommended"]
    assert recommendation["explanation"]
    assert "history_signal" in recommendation
    assert "is_critical" in recommendation["affected_skills"][0]


def test_declined_history_lowers_priority_score():
    result = get_employee_recommendations("E0002")
    event_id = result["recommendations"][0]["event_id"]
    before = next(item["score"] for item in result["recommendations"] if item["event_id"] == event_id)
    db = SessionLocal()
    try:
        for old_record in db.query(ActivityHistory).filter(ActivityHistory.record_id.like("TEST_DECLINED_%")).all():
            db.delete(old_record)
        db.commit()
        db.add(ActivityHistory(
            record_id=f"TEST_DECLINED_{event_id}",
            employee_id="E0002",
            event_id=event_id,
            date=date.today(),
            status="declined",
        ))
        db.commit()
    finally:
        db.close()

    after_item = next(item for item in get_employee_recommendations("E0002")["recommendations"] if item["event_id"] == event_id)
    assert after_item["score"] <= before
    assert after_item["history_signal"]["missed_or_declined_similar"] >= 1


def test_completion_updates_skill_progress_and_coins():
    result = complete_quest("E0002", "EV_005")

    assert result["updated_skills"]
    assert result["progress_to_next_grade_after"] >= result["progress_to_next_grade_before"]
    assert result["coins_earned"] > 0
    assert result["wallet_balance"] >= result["coins_earned"]


def test_mandatory_completion_awards_no_coins():
    result = complete_quest("E0002", "EV_001")

    assert result["coins_earned"] == 0
    assert result["coin_reason"].startswith("Mandatory event")


def test_game_map_projects_recommendations():
    game_map = get_game_map("E0002")

    assert game_map["city_name"] == "Career City"
    assert game_map["quest_board"]
    assert all(item["source"] == "recommendation_engine" for item in game_map["quest_board"])
    assert {district["id"] for district in game_map["districts"]} >= {"engineering", "security", "communication", "leadership"}


def test_completed_similar_course_does_not_hide_other_eligible_courses():
    with SessionLocal() as db:
        db.add(Employee(employee_id="TEST", full_name="Test", role="Test Engineer", grade="Junior", skills={"skill": 1}))
        db.add(RoleProfile(role="Test Engineer", grade="Middle", required_skills={"skill": 4}))
        for event_id in ["COMPLETED", "AVAILABLE"]:
            db.add(Event(event_id=event_id, title=event_id, type="course", target_roles=["Test Engineer"], develops_skills=[{"skill_id": "skill", "gain": 1, "max_level": 5}]))
        db.add(ActivityHistory(record_id="TEST_HISTORY", employee_id="TEST", event_id="COMPLETED", status="completed", date=date.today()))
        db.commit()

    recommendations = get_employee_recommendations("TEST")["recommendations"]
    assert [item["event_id"] for item in recommendations] == ["AVAILABLE"]
    assert recommendations[0]["history_signal"]["completed_similar"] == 1
    assert recommendations[0]["history_signal"]["already_completed_this_event"] is False


def test_recommendations_require_all_prerequisites_and_actual_skill_gain():
    with SessionLocal() as db:
        db.add(Employee(employee_id="TEST", full_name="Test", role="Test Engineer", grade="Junior", skills={"skill": 2}))
        db.add(RoleProfile(role="Test Engineer", grade="Middle", required_skills={"skill": 4}))
        db.add(Event(event_id="PREREQUISITE", title="Prerequisite", target_roles=["Test Engineer"], prerequisites={"other_skill": 2}, develops_skills=[{"skill_id": "skill", "gain": 1, "max_level": 5}]))
        db.add(Event(event_id="CAPPED", title="Capped", target_roles=["Test Engineer"], develops_skills=[{"skill_id": "skill", "gain": 1, "max_level": 2}]))
        db.commit()

    assert get_employee_recommendations("TEST")["recommendations"] == []


@pytest.mark.parametrize("event_id", ["EV_005", "EV_036", "EV_001"])
def test_repeated_completion_does_not_award_duplicate_skills_or_coins(event_id):
    complete_quest("E0002", event_id)
    profile_before = get_employee_profile("E0002")
    map_before = get_game_map("E0002")
    with SessionLocal() as db:
        count_before = db.query(ActivityHistory).filter_by(employee_id="E0002", event_id=event_id).count()

    with pytest.raises(HTTPException) as error:
        complete_quest("E0002", event_id)

    assert error.value.status_code == 409
    assert get_employee_profile("E0002")["skills"] == profile_before["skills"]
    assert get_game_map("E0002")["center"]["wallet_balance"] == map_before["center"]["wallet_balance"]
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(employee_id="E0002", event_id=event_id).count() == count_before


def test_repeatable_club_can_be_completed_on_a_later_day():
    with SessionLocal() as db:
        db.add(ActivityHistory(record_id="OLDER_CLUB", employee_id="E0002", event_id="EV_036", status="completed", date=date(2025, 1, 1)))
        db.commit()
    result = complete_quest("E0002", "EV_036")
    assert result["coins_earned"] > 0


def test_reward_failure_rolls_back_history_skills_and_wallet():
    skills_before = get_employee_profile("E0002")["skills"]
    with SessionLocal() as db:
        count_before = db.query(ActivityHistory).filter_by(employee_id="E0002").count()

    def fail_reward(mapper, connection, target):
        raise RuntimeError("Simulated reward failure")

    sqlalchemy_event.listen(CoinTransaction, "before_insert", fail_reward)
    try:
        with pytest.raises(RuntimeError, match="Simulated reward failure"):
            complete_quest("E0002", "EV_005")
    finally:
        sqlalchemy_event.remove(CoinTransaction, "before_insert", fail_reward)

    assert get_employee_profile("E0002")["skills"] == skills_before
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(employee_id="E0002").count() == count_before
        assert db.get(Wallet, "E0002") is None
