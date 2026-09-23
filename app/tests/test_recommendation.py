from datetime import date

from app.db.database import SessionLocal, init_db
from app.db.models import ActivityHistory, Employee
from app.services.game_service import get_game_map
from app.services.esg_service import list_goals
from app.services.import_service import register_employee, seed_demo_data
from app.services.pair_service import create_invitation, get_pair_space, list_invitations, preview_invitation, respond_to_invitation
from app.services.quest_service import get_quest_steps
from app.services.recommendation_service import complete_quest, get_employee_recommendations
from app.services.quest_service import select_quest
from app.services.team_service import create_team, join_team


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
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_001").delete()
        db.commit()
    result = complete_quest("E0002", "EV_001")

    assert result["coins_earned"] == 0
    assert result["coin_reason"].startswith("Mandatory event")


def test_game_map_projects_recommendations():
    game_map = get_game_map("E0002")

    assert game_map["city_name"] == "Career City"
    assert game_map["quest_board"]
    assert all(item["source"] == "recommendation_engine" for item in game_map["quest_board"])
    assert {district["id"] for district in game_map["districts"]} >= {"engineering", "security", "communication", "leadership"}


def test_recommendations_return_top_three_with_scoring_breakdown():
    result = get_employee_recommendations("E0002")

    assert 1 <= len(result["recommendations"]) <= 3
    assert all(set(item["scoring_factors"]) == {
        "skill_gap_score",
        "critical_skill_score",
        "event_impact_score",
        "role_grade_relevance_score",
        "history_score",
        "prerequisite_score",
    } for item in result["recommendations"])


def test_jury_registration_selection_team_and_esg_catalog():
    db = SessionLocal()
    try:
        old = db.get(Employee, "E_JURY_TEST")
        if old:
            db.delete(old)
            db.commit()
    finally:
        db.close()

    registration = register_employee({
        "employee_id": "E_JURY_TEST",
        "full_name": "Jury Test Employee",
        "role": "Backend Engineer",
        "grade": "Middle",
        "career_goal": {"target_role": "Backend Engineer", "target_grade": "Senior"},
        "skills": {"SK_PYTHON": 3, "SK_SYSTEM_DESIGN": 1},
    })
    assert registration["employee_id"] == "E_JURY_TEST"
    assert get_employee_recommendations("E_JURY_TEST")["recommendations"]

    selected = select_quest("E_JURY_TEST", "EV_005")
    assert selected["status"] == "selected"
    team = create_team({"name": "Jury Team", "creator_id": "E_JURY_TEST", "max_members": 2})
    assert join_team(team["team_id"], "E0002")["member_ids"]
    assert list_goals()


def test_pair_invitation_hides_scoring_and_creates_space_after_eligible_response():
    register_employee({
        "employee_id": "E_JURY_TEST", "full_name": "Pair Eligible Employee",
        "role": "Backend Engineer", "grade": "Middle",
        "career_goal": {"target_role": "Backend Engineer", "target_grade": "Senior"},
        "skills": {"SK_PYTHON": 3, "SK_SYSTEM_DESIGN": 1},
    })
    register_employee({
        "employee_id": "E_PAIR_NOT_MATCH",
        "full_name": "Pair Not Match",
        "role": "HR Business Partner",
        "grade": "Middle",
        "career_goal": {"target_role": "HR Business Partner", "target_grade": "Senior"},
        "skills": {},
    })
    select_quest("E0002", "EV_005")
    invitation = create_invitation({
        "inviter_id": "E0002",
        "event_id": "EV_005",
        "start_date": "2026-10-01",
        "end_date": "2026-10-07",
        "format": "online_together",
        "display_mode": "alias",
        "display_name": "Алия",
    })

    assert invitation["activity_title"] == "System Design Fundamentals"
    assert "score" not in invitation
    assert "skill_gaps" not in invitation
    assert invitation["display_name"] == "Алия"

    preview = preview_invitation(invitation["invitation_id"], "E_PAIR_NOT_MATCH")
    assert preview["eligible"] is False
    assert "score" not in preview
    assert "skill_gaps" not in preview

    response = respond_to_invitation(invitation["invitation_id"], {"employee_id": "E_PAIR_NOT_MATCH", "decision": "accept"})
    assert response["status"] == "not_a_match"

    response = respond_to_invitation(invitation["invitation_id"], {"employee_id": "E_JURY_TEST", "decision": "accept"})
    assert response["status"] == "accepted"
    pair = get_pair_space(response["pair_id"])
    assert pair["members"] == ["E0002", "E_JURY_TEST"]
    assert list_invitations("E0002") == []


def test_quest_steps_are_available_without_requiring_openai():
    result = get_quest_steps("E0002", "EV_005")

    assert result["event_id"] == "EV_005"
    assert result["provider"] in {"template", "openai"}
    assert 3 <= len(result["steps"]) <= 5
    assert all({"step", "title", "description", "done"} <= set(step) for step in result["steps"])
