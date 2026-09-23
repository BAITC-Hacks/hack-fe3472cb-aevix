"""Regressions for the workspace contracts and newly connected quest workflow."""
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from threading import Event as ThreadEvent

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, CoinTransaction, Employee, Event, QuestProgress, Wallet
from app.main import app
from app.services import recommendation_service
from app.services.game_service import get_game_map, get_game_progress
from app.services.quest_service import select_quest
from app.services.recommendation_service import complete_quest, get_employee_profile, get_employee_recommendations
from app.services.team_service import complete_team_quest, create_team, get_team, join_team, start_team_quest


def test_recommendation_http_explanations_are_opt_in_and_validate_queries(monkeypatch, employee_sign_in):
    calls = []

    def explain(context, candidates):
        calls.append(context["language"])
        return {"provider": "template", "summary": "HTTP test", "recommendation_explanations": []}

    monkeypatch.setattr(recommendation_service, "explain_recommendations", explain)
    with TestClient(app) as client:
        employee_sign_in(client)
        for route in ("/api/employees/E0002/recommendations", "/api/recommendations/E0002"):
            assert client.get(route).status_code == 200
            assert calls == []
            response = client.get(route, params={"include_explanations": "true", "language": "kk", "limit": 1})
            assert response.status_code == 200
            assert len(response.json()["recommendations"]) == 1
            assert calls.pop() == "kk"
            for params in ({"language": "invalid"}, {"limit": 0}, {"include_explanations": "invalid"}):
                assert client.get(route, params=params).status_code == 422


def test_employee_registration_rejects_invalid_fields(hr_sign_in):
    with TestClient(app) as client:
        hr_sign_in(client)
        for payload in ({}, {"employee_id": " ", "full_name": "Name"},
                        {"employee_id": "INVALID", "full_name": " "},
                        {"employee_id": "INVALID", "full_name": "Name", "skills": {"SK_PYTHON": -1}}):
            assert client.post("/api/employees/register", json=payload).status_code == 422
    with SessionLocal() as db:
        assert db.get(Employee, "INVALID") is None


def test_select_then_complete_persists_one_learning_entry_and_one_reward():
    employee_id, event_id = "E0002", "EV_005"
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).delete()
        db.commit()
    select_quest(employee_id, event_id)
    select_quest(employee_id, event_id)
    with SessionLocal() as db:
        history = db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id).all()
        assert len(history) == 1
        assert history[0].status == "in_progress"
        assert db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).count() == 1
    result = complete_quest(employee_id, event_id)
    persisted = get_employee_profile(employee_id)
    assert all(persisted["skills"][skill_id] == values["after"] for skill_id, values in result["updated_skills"].items())
    assert result["progress_to_next_grade_after"] == persisted["progress_to_next_grade"]
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id, status="completed").count() == 1
        assert db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id).one().completed_at == date.today()
    for action in (select_quest, complete_quest):
        with pytest.raises(HTTPException) as error:
            action(employee_id, event_id)
        assert error.value.status_code == 409
    with SessionLocal() as db:
        assert db.get(Wallet, employee_id).balance == result["wallet_balance"]
        assert db.query(CoinTransaction).filter_by(employee_id=employee_id, event_id=event_id).count() == 1


def test_failed_completion_rolls_back_skills_history_wallet_and_selection(monkeypatch):
    before = get_employee_profile("E0002")
    select_quest("E0002", "EV_005")

    def fail_selection_update(*args):
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(recommendation_service, "mark_quest_completed", fail_selection_update)
    with pytest.raises(RuntimeError):
        complete_quest("E0002", "EV_005")
    assert get_employee_profile("E0002")["skills"] == before["skills"]
    with SessionLocal() as db:
        assert db.query(CoinTransaction).filter_by(employee_id="E0002", event_id="EV_005").count() == 0
        assert db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005", status="in_progress").count() == 1
        assert db.query(QuestProgress).filter_by(employee_id="E0002", event_id="EV_005").one().status == "selected"


def test_completion_adds_reward_to_existing_wallet():
    with SessionLocal() as db:
        db.merge(Wallet(employee_id="E0002", balance=75))
        db.commit()
    result = complete_quest("E0002", "EV_005")
    with SessionLocal() as db:
        assert result["wallet_balance"] == db.get(Wallet, "E0002").balance == 75 + result["coins_earned"]


def test_selecting_registered_course_moves_it_into_active_learning():
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005").delete()
        db.add(ActivityHistory(record_id="REG_REGISTERED", employee_id="E0002", event_id="EV_005", status="registered"))
        db.commit()
    select_quest("E0002", "EV_005")
    with SessionLocal() as db:
        records = db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005").all()
        assert len(records) == 1
        assert records[0].status == "in_progress"


def test_concurrent_completion_cannot_award_twice(monkeypatch):
    entered_first = ThreadEvent()
    release_first = ThreadEvent()
    entered_second = ThreadEvent()
    started_second = ThreadEvent()
    original = recommendation_service._complete_quest

    def hold_first_transaction(db, employee_id, event_id):
        if not entered_first.is_set():
            entered_first.set()
            assert release_first.wait(timeout=5)
        else:
            entered_second.set()
        return original(db, employee_id, event_id)

    def second_request():
        started_second.set()
        return complete_quest("E0002", "EV_005")

    monkeypatch.setattr(recommendation_service, "_complete_quest", hold_first_transaction)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(complete_quest, "E0002", "EV_005")
        assert entered_first.wait(timeout=5)
        second = pool.submit(second_request)
        try:
            assert started_second.wait(timeout=5)
            assert not entered_second.wait(timeout=0.15)
        finally:
            release_first.set()
        result = first.result(timeout=5)
        with pytest.raises(HTTPException) as error:
            second.result(timeout=5)
        assert error.value.status_code == 409
    with SessionLocal() as db:
        assert db.query(CoinTransaction).filter_by(employee_id="E0002", event_id="EV_005").count() == 1
        assert db.get(Wallet, "E0002").balance == result["wallet_balance"]


def test_unmet_prerequisites_block_selection_and_direct_completion():
    with SessionLocal() as db:
        db.add(Event(event_id="REG_LOCKED", title="Locked course", duration_hours=10, mandatory=False,
                     prerequisites={"SK_NONEXISTENT": 3}))
        db.commit()
    for action in (select_quest, complete_quest):
        with pytest.raises(HTTPException) as error:
            action("E0002", "REG_LOCKED")
        assert error.value.status_code == 409
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(event_id="REG_LOCKED").count() == 0
        assert db.query(CoinTransaction).filter_by(event_id="REG_LOCKED").count() == 0


def test_completing_similar_event_does_not_hide_new_courses():
    with SessionLocal() as db:
        db.add_all([
            Event(event_id="REG_DONE", title="Previous course", type="regression_type", mandatory=False),
            Event(event_id="REG_NEXT", title="Next course", type="regression_type", mandatory=False,
                  develops_skills=[{"skill_id": "SK_SYSTEM_DESIGN", "gain": 1, "max_level": 5}]),
            ActivityHistory(record_id="REG_HISTORY", employee_id="E0002", event_id="REG_DONE", status="completed"),
        ])
        db.commit()
    result = get_employee_recommendations("E0002", limit=100, use_llm=False)
    item = next(item for item in result["recommendations"] if item["event_id"] == "REG_NEXT")
    assert item["history_signal"]["completed_similar"] == 1
    assert not item["history_signal"]["already_completed_this_event"]


def test_recommendations_check_every_prerequisite_and_exclude_zero_gain():
    with SessionLocal() as db:
        skill_level = db.get(Employee, "E0002").skills.get("SK_SYSTEM_DESIGN", 0)
        db.add_all([
            Event(event_id="REG_LOCKED", title="Advanced course", mandatory=False,
                  prerequisites={"SK_NONEXISTENT": 3},
                  develops_skills=[{"skill_id": "SK_SYSTEM_DESIGN", "gain": 1, "max_level": 5}]),
            Event(event_id="REG_CAPPED", title="Beginner course", mandatory=False,
                  develops_skills=[{"skill_id": "SK_SYSTEM_DESIGN", "gain": 1, "max_level": skill_level}]),
        ])
        db.commit()
    ids = {item["event_id"] for item in get_employee_recommendations("E0002", limit=100, use_llm=False)["recommendations"]}
    assert not ids.intersection({"REG_LOCKED", "REG_CAPPED"})


def test_game_load_does_not_call_llm(monkeypatch):
    def unexpected_llm(*args):
        pytest.fail("City endpoints must not generate duplicate agent requests")
    monkeypatch.setattr(recommendation_service, "explain_recommendations", unexpected_llm)
    assert get_game_map("E0002")["city_progress"]
    assert get_game_progress("E0002")["city_progress"]


def test_agent_language_and_deterministic_explanation_are_preserved(monkeypatch):
    def explanation(context, candidates):
        assert context["language"] == "kk"
        return {
            "provider": "openai", "summary": "Agent summary",
            "recommendation_explanations": [{
                "event_id": item["event_id"], "explanation": "Agent explanation",
                "employee_friendly_reason": "Reason", "risk_note": "Risk", "expected_outcome": "Outcome",
            } for item in candidates],
        }
    monkeypatch.setattr(recommendation_service, "explain_recommendations", explanation)
    result = get_employee_recommendations("E0002", language="kk")
    assert result["explanation_provider"] == "openai"
    for item in result["recommendations"]:
        assert item["agent_explanation"] == "Agent explanation"
        assert item["explanation"] != item["agent_explanation"]


def test_team_completion_rolls_back_if_one_member_cannot_complete():
    with SessionLocal() as db:
        db.add(Event(event_id="REG_TEAM", title="Team quest", duration_hours=1, mandatory=False))
        db.commit()
    team = create_team({"creator_id": "E0002", "name": "Atomic team"})
    join_team(team["team_id"], "E0001")
    complete_quest("E0001", "REG_TEAM")
    with pytest.raises(HTTPException) as error:
        complete_team_quest(team["team_id"], "REG_TEAM")
    assert error.value.status_code == 409
    assert get_team(team["team_id"])["completed_team_quests"] == 0
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="REG_TEAM").count() == 0
        assert db.query(CoinTransaction).filter_by(employee_id="E0002", event_id="REG_TEAM").count() == 0


def test_team_start_adds_learning_for_members_and_repeats_do_not_reward():
    with SessionLocal() as db:
        db.add(Event(event_id="REG_TEAM", title="Team quest", duration_hours=1, mandatory=False))
        db.commit()
    team = create_team({"creator_id": "E0002", "name": "Learning team"})
    join_team(team["team_id"], "E0001")
    start_team_quest(team["team_id"], "REG_TEAM")
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(event_id="REG_TEAM", status="in_progress").count() == 2
        assert db.query(QuestProgress).filter_by(event_id="REG_TEAM", mode="team").count() == 2
    result = complete_team_quest(team["team_id"], "REG_TEAM")
    assert result["completed_team_quests"] == 1
    assert len(result["member_results"]) == 2
    with pytest.raises(HTTPException) as error:
        complete_team_quest(team["team_id"], "REG_TEAM")
    assert error.value.status_code == 409
    assert get_team(team["team_id"])["completed_team_quests"] == 1
