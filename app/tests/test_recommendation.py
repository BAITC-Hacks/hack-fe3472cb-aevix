from datetime import date

from app.db.database import SessionLocal, init_db
from app.db.models import ActivityHistory
from app.services.game_service import get_game_map
from app.services.import_service import seed_demo_data
from app.services.recommendation_service import complete_quest, get_employee_recommendations


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
