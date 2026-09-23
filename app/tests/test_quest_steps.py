"""Persisted plans, learning progress and rewards share the isolated test database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier, Event as ThreadEvent

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event as sqlalchemy_event

from app.db import database
from app.db.database import SessionLocal
from app.db.models import ActivityHistory, CoinTransaction, Employee, Event, QuestPlan, QuestProgress, QuestStepProgress
from app.main import app
from app.services import quest_service
from app.services.game_service import get_game_map
from app.services.quest_service import complete_quest_step, get_quest_steps, select_quest
from app.services.recommendation_service import complete_quest, get_employee_profile, get_employee_trajectory


def test_plan_content_and_language_are_persisted_once(monkeypatch):
    calls = []

    def generate(event, employee, language="ru"):
        calls.append((event["event_id"], employee["employee_id"], language))
        return {"provider": "openai", "steps": [
            {"step": number, "title": f"Task {number}", "description": f"Practice {number}", "done": True}
            for number in range(1, 4)
        ]}

    monkeypatch.setattr(quest_service, "generate_quest_steps", generate)
    with SessionLocal() as db:
        # The overwritten backend stored numbers without the plan those numbers meant.
        db.add(QuestStepProgress(employee_id="E0002", event_id="EV_005", step_number=1, status="completed"))
        db.commit()
    first = get_quest_steps("E0002", "EV_005", language="kk")
    assert first["language"] == "kk"
    assert first["provider"] == "openai"
    assert not any(step["done"] for step in first["steps"])
    with SessionLocal() as db:
        db.get(Event, "EV_005").title = "Changed catalog title"
        db.get(Employee, "E0002").skills = {"SK_SYSTEM_DESIGN": 4}
        db.commit()
    assert get_quest_steps("E0002", "EV_005", language="en") == first
    assert calls == [("EV_005", "E0002", "kk")]
    with SessionLocal() as db:
        assert db.query(QuestPlan).count() == 1
        assert db.query(QuestStepProgress).count() == 0


def test_steps_update_learning_then_final_completion_awards_once():
    select_quest("E0002", "EV_005")
    plan = get_quest_steps("E0002", "EV_005")
    original_city = get_game_map("E0002")["city_progress"]["completed_courses"]
    first = complete_quest_step("E0002", "EV_005", 1)
    assert first["completed_steps"] == 1
    assert first["completion_pct"] == 25
    assert not first["can_complete"]
    assert complete_quest_step("E0002", "EV_005", 1) == first
    with SessionLocal() as db:
        assert db.query(QuestStepProgress).filter_by(employee_id="E0002", event_id="EV_005").count() == 1
        assert db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005", status="in_progress").one().completion_pct == 25
        assert db.query(CoinTransaction).count() == 0
    with pytest.raises(HTTPException) as error:
        complete_quest("E0002", "EV_005")
    assert error.value.status_code == 409
    assert get_game_map("E0002")["city_progress"]["completed_courses"] == original_city
    for step in plan["steps"][1:]:
        result = complete_quest_step("E0002", "EV_005", step["step"])
    assert result["can_complete"]
    assert result["completion_pct"] == 100
    history = [row for row in get_employee_trajectory("E0002") if row["event_id"] == "EV_005"]
    assert all(row["completed_steps"] == row["total_steps"] == 4 for row in history)
    reward = complete_quest("E0002", "EV_005")
    assert reward["coins_earned"] > 0
    profile = get_employee_profile("E0002")
    assert all(profile["skills"][key] == value["after"] for key, value in reward["updated_skills"].items())
    assert get_game_map("E0002")["city_progress"]["completed_courses"] == original_city + 1
    assert get_quest_steps("E0002", "EV_005")["status"] == "completed"
    assert not get_quest_steps("E0002", "EV_005")["can_complete"]
    with pytest.raises(HTTPException) as error:
        complete_quest("E0002", "EV_005")
    assert error.value.status_code == 409
    with SessionLocal() as db:
        assert db.query(CoinTransaction).filter_by(employee_id="E0002", event_id="EV_005").count() == 1


def test_preview_requires_selection_and_unknown_steps_never_write():
    with SessionLocal() as db:
        db.add(Event(event_id="STEPS_NEW", title="New training", mandatory=False))
        db.commit()
    with pytest.raises(HTTPException) as error:
        complete_quest_step("E0002", "STEPS_NEW", 1)
    assert error.value.status_code == 409
    plan = get_quest_steps("E0002", "STEPS_NEW")
    assert plan["status"] == "recommended"
    with pytest.raises(HTTPException) as error:
        complete_quest_step("E0002", "STEPS_NEW", 1)
    assert error.value.status_code == 409
    select_quest("E0002", "STEPS_NEW")
    for number in (0, 99, True):
        with pytest.raises(HTTPException) as error:
            complete_quest_step("E0002", "STEPS_NEW", number)
        assert error.value.status_code == 422
    with SessionLocal() as db:
        assert db.query(QuestStepProgress).count() == 0
        assert db.query(CoinTransaction).count() == 0


def test_legacy_active_training_can_complete_steps_without_duplicate_history():
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005").delete()
        db.add(ActivityHistory(record_id="LEGACY_STEPS", employee_id="E0002", event_id="EV_005", status="in_progress", completion_pct=10))
        db.commit()
    get_quest_steps("E0002", "EV_005")
    complete_quest_step("E0002", "EV_005", 1)
    with SessionLocal() as db:
        records = db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005").all()
        assert len(records) == 1
        assert records[0].completion_pct == 25
        assert db.query(QuestProgress).filter_by(employee_id="E0002", event_id="EV_005").one().status == "selected"


def test_concurrent_plan_reads_generate_once_without_blocking_selection(monkeypatch):
    entered = ThreadEvent()
    release = ThreadEvent()
    calls = []
    original = quest_service.generate_quest_steps

    def generate(*args, **kwargs):
        calls.append(1)
        entered.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(quest_service, "generate_quest_steps", generate)
    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(get_quest_steps, "E0002", "EV_005")
        assert entered.wait(timeout=5)
        second = pool.submit(get_quest_steps, "E0002", "EV_005")
        try:
            selected = pool.submit(select_quest, "E0002", "EV_005").result(timeout=3)
            assert selected["status"] == "selected"
        finally:
            release.set()
        assert first.result(timeout=5) == second.result(timeout=5)
    assert calls == [1]
    with SessionLocal() as db:
        assert db.query(QuestPlan).count() == 1


def test_concurrent_step_requests_persist_one_completion():
    select_quest("E0002", "EV_005")
    get_quest_steps("E0002", "EV_005")
    barrier = Barrier(2)

    def complete():
        barrier.wait(timeout=5)
        return complete_quest_step("E0002", "EV_005", 1)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete) for _ in range(2)]
        assert all(future.result(timeout=5)["completed_steps"] == 1 for future in futures)
    with SessionLocal() as db:
        assert db.query(QuestStepProgress).count() == 1


def test_failed_step_update_rolls_back_marker_and_learning_progress():
    select_quest("E0002", "EV_005")
    get_quest_steps("E0002", "EV_005")

    def fail_update(_conn, _cursor, statement, _params, _context, _many):
        if statement.startswith("UPDATE activity_history"):
            raise RuntimeError("Failed to persist learning progress")

    sqlalchemy_event.listen(database.engine, "before_cursor_execute", fail_update)
    try:
        with pytest.raises(RuntimeError, match="Failed to persist"):
            complete_quest_step("E0002", "EV_005", 1)
    finally:
        sqlalchemy_event.remove(database.engine, "before_cursor_execute", fail_update)
    with SessionLocal() as db:
        assert db.query(QuestStepProgress).count() == 0
        assert db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_005", status="in_progress").one().completion_pct == 0


def test_recurring_participation_reuses_plan_but_resets_step_markers():
    with SessionLocal() as db:
        db.query(ActivityHistory).filter_by(employee_id="E0002", event_id="EV_036").delete()
        db.commit()
    select_quest("E0002", "EV_036")
    plan = get_quest_steps("E0002", "EV_036")
    for step in plan["steps"]:
        complete_quest_step("E0002", "EV_036", step["step"])
    complete_quest("E0002", "EV_036")
    select_quest("E0002", "EV_036")
    again = get_quest_steps("E0002", "EV_036")
    assert again["steps"] == plan["steps"]
    assert again["completed_steps"] == 0
    with pytest.raises(HTTPException) as error:
        complete_quest("E0002", "EV_036")
    assert error.value.status_code == 409
    with SessionLocal() as db:
        assert db.query(QuestPlan).count() == 1
        assert db.query(CoinTransaction).filter_by(employee_id="E0002", event_id="EV_036").count() == 1


def test_plans_are_employee_specific():
    first = get_quest_steps("E0002", "EV_005")
    other = get_quest_steps("E0001", "EV_005")
    assert first["employee_id"] != other["employee_id"]
    select_quest("E0002", "EV_005")
    complete_quest_step("E0002", "EV_005", 1)
    assert get_quest_steps("E0001", "EV_005")["completed_steps"] == 0
    with SessionLocal() as db:
        assert db.query(QuestPlan).count() == 2


def test_trajectory_preserves_recurring_history_and_only_adds_missing_progress():
    with SessionLocal() as db:
        db.add_all([
            Event(event_id="STEPS_RECURRING", title="Recurring activity"),
            Event(event_id="STEPS_ORPHAN", title="Selected activity"),
            ActivityHistory(record_id="STEPS_HISTORY_1", employee_id="E0002", event_id="STEPS_RECURRING", status="completed"),
            ActivityHistory(record_id="STEPS_HISTORY_2", employee_id="E0002", event_id="STEPS_RECURRING", status="completed"),
            QuestProgress(employee_id="E0002", event_id="STEPS_RECURRING", status="completed", mode="solo", completed_at=date.today()),
            QuestProgress(employee_id="E0002", event_id="STEPS_ORPHAN", status="selected", mode="solo"),
        ])
        db.commit()
    rows = get_employee_trajectory("E0002")
    recurring = [row for row in rows if row["event_id"] == "STEPS_RECURRING"]
    assert len(recurring) == 2
    assert all(row["source"] == "activity_history" for row in recurring)
    orphan = [row for row in rows if row["event_id"] == "STEPS_ORPHAN"]
    assert len(orphan) == 1
    assert orphan[0]["source"] == "quest_progress"
    select_quest("E0002", "STEPS_ORPHAN")
    active = [row for row in get_employee_trajectory("E0002") if row["event_id"] == "STEPS_ORPHAN"]
    assert len(active) == 1
    assert active[0]["source"] == "activity_history"


@pytest.mark.parametrize("employee_id,event_id", [("MISSING", "EV_005"), ("E0002", "MISSING")])
def test_unknown_plan_participants_return_404(employee_id, event_id):
    for action in (get_quest_steps, lambda employee, event: complete_quest_step(employee, event, 1)):
        with pytest.raises(HTTPException) as error:
            action(employee_id, event_id)
        assert error.value.status_code == 404


def test_quest_step_http_routes_preserve_plan_and_gate_final_completion(employee_sign_in):
    base = "/api/employees/E0002/quests/EV_005"
    with TestClient(app) as client:
        employee_sign_in(client)
        assert client.get(base + "/steps", params={"language": "invalid"}).status_code == 422
        assert client.get("/api/employees/MISSING/quests/EV_005/steps").status_code == 403
        assert client.post(base + "/select").status_code == 200
        response = client.get(base + "/steps", params={"language": "en"})
        assert response.status_code == 200
        plan = response.json()
        assert plan["language"] == "en"
        assert plan["task"]["event_id"] == "EV_005"
        assert client.post(base + "/steps/99/complete").status_code == 422
        assert client.post(base + "/complete").status_code == 409
        for step in plan["steps"]:
            response = client.post(base + f"/steps/{step['step']}/complete")
            assert response.status_code == 200
        assert response.json()["can_complete"]
        refreshed = client.get(base + "/steps", params={"language": "ru"}).json()
        assert refreshed["language"] == "en"
        assert all(step["done"] for step in refreshed["steps"])
        assert client.post(base + "/complete").status_code == 200
        assert client.post(base + "/complete").status_code == 409
