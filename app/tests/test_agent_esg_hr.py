"""Regressions from the agent, wallet and HR update; all data uses the test DB."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

from fastapi import FastAPI, HTTPException
import pytest
from sqlalchemy import event

from app.db import database
from app.db.database import SessionLocal
from app.db.models import ActivityHistory, CoinTransaction, Employee, ESGContribution, RoleProfile, Skill, Wallet
from app.routers import esg_router, wallet_router
from app.services import esg_service, hr_service, llm_service


def api_request(method, path, payload=None):
    """Exercise FastAPI request validation without requiring an HTTP client package."""
    app = FastAPI()
    app.include_router(esg_router.router, prefix="/esg")
    app.include_router(wallet_router.router, prefix="/wallet")
    messages = []

    async def receive():
        return {"type": "http.request", "body": json.dumps(payload).encode(), "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": [(b"content-type", b"application/json")],
        "server": ("test", 80), "client": ("test", 1234), "root_path": "",
    }, receive, send))
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, json.loads(body)


@pytest.mark.parametrize("payload", [
    {}, {"employee_id": "E0002"}, {"coins": 10},
    {"employee_id": "E0002", "coins": "oops"},
    {"employee_id": "E0002", "coins": "10"},
    {"employee_id": "E0002", "coins": 1.5},
    {"employee_id": "E0002", "coins": True},
    {"employee_id": "E0002", "coins": 0},
    {"employee_id": "E0002", "coins": -10},
    {"employee_id": "E0002", "coins": 2**63},
    {"employee_id": "  ", "coins": 10},
])
def test_esg_rejects_invalid_payload_without_server_error(payload):
    status, _ = api_request("POST", "/esg/ESG_GREEN_OFFICE/contribute", payload)
    assert status == 422
    with SessionLocal() as db:
        assert db.query(ESGContribution).count() == 0
        assert db.query(CoinTransaction).count() == 0


def test_esg_and_wallet_validate_employee_and_expose_goal_target():
    assert api_request("GET", "/wallet/missing")[0] == 404
    assert api_request("POST", "/esg/ESG_GREEN_OFFICE/contribute", {"employee_id": "missing", "coins": 10})[0] == 404
    with SessionLocal() as db:
        db.add(Wallet(employee_id="E0002", balance=100))
        db.commit()
    status, result = api_request("POST", "/esg/ESG_GREEN_OFFICE/contribute", {"employee_id": "E0002", "coins": 40})
    assert status == 200
    assert result["target_coins"] == 1000
    assert result["wallet_balance"] == 60
    assert result["total_contributed_coins"] == 40
    assert result["contributors_count"] == 1
    with SessionLocal() as db:
        assert db.query(CoinTransaction).one().amount == -40


def test_concurrent_esg_donations_cannot_overdraw_wallet():
    esg_service.ensure_goals()
    with SessionLocal() as db:
        db.add(Wallet(employee_id="E0002", balance=100))
        db.commit()
    barrier = Barrier(2)

    def donate():
        barrier.wait(timeout=5)
        try:
            esg_service.contribute("ESG_GREEN_OFFICE", "E0002", 80)
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(donate) for _ in range(2)]
        assert sorted(future.result(timeout=10) for future in futures) == [200, 409]
    with SessionLocal() as db:
        assert db.get(Wallet, "E0002").balance == 20
        assert db.query(ESGContribution).one().coins == 80
        assert db.query(CoinTransaction).one().amount == -80


def test_failed_contribution_rolls_back_debit_and_ledger():
    esg_service.ensure_goals()
    with SessionLocal() as db:
        db.add(Wallet(employee_id="E0002", balance=100))
        db.commit()

    def fail_contribution_insert(_conn, _cursor, statement, _params, _context, _many):
        if statement.startswith("INSERT INTO esg_contributions"):
            raise RuntimeError("Simulated write failure")

    event.listen(database.engine, "before_cursor_execute", fail_contribution_insert)
    try:
        with pytest.raises(RuntimeError, match="Simulated write failure"):
            esg_service.contribute("ESG_GREEN_OFFICE", "E0002", 80)
    finally:
        event.remove(database.engine, "before_cursor_execute", fail_contribution_insert)
    with SessionLocal() as db:
        assert db.get(Wallet, "E0002").balance == 100
        assert db.query(ESGContribution).count() == 0
        assert db.query(CoinTransaction).count() == 0


def test_hr_counts_actual_target_gaps_inactivity_and_learning_completion(monkeypatch):
    monkeypatch.setattr(hr_service, "get_employee_recommendations", lambda *_args, **_kwargs: {"recommendations": []})
    with SessionLocal() as db:
        db.query(ActivityHistory).delete()
        db.query(Employee).delete()
        db.query(RoleProfile).delete()
        db.query(Skill).delete()
        db.add_all([
            Skill(skill_id="TEST_A", name="Architecture", type="hard"),
            Skill(skill_id="TEST_MISSING", name="Planning", type="hard"),
            RoleProfile(role="Reviewer", grade="Senior", required_skills={"TEST_A": 3, "TEST_MISSING": 4}),
            RoleProfile(role="Reviewer", grade="Lead", required_skills={"TEST_A": 5}),
            RoleProfile(role="Unrelated", grade="Senior", required_skills={"TEST_UNRELATED": 5}),
            Employee(employee_id="TEST_ACTIVE", full_name="Active", role="Reviewer", grade="Middle", skills={"TEST_A": 3, "TEST_UNRELATED": 0}),
            Employee(employee_id="TEST_INACTIVE", full_name="Inactive", role="Reviewer", grade="Lead", skills={}),
            Employee(employee_id="TEST_NEW", full_name="New", role="Reviewer", grade="Lead", skills={}),
            ActivityHistory(record_id="TEST_COMPLETED", employee_id="TEST_ACTIVE", event_id="EV_005", status="completed"),
            ActivityHistory(record_id="TEST_MISSED", employee_id="TEST_INACTIVE", event_id="EV_005", status="no_show"),
        ])
        db.commit()
    result = hr_service.get_hr_dashboard()
    assert result["events_completion_rate"] == 0.5
    assert result["inactive_employees_count"] == 2
    assert result["risky_segments"] == ["Lead"]
    gaps = {gap["skill_id"]: gap for gap in result["top_skill_gaps"]}
    assert set(gaps) == {"TEST_A", "TEST_MISSING"}
    assert gaps["TEST_A"]["affected_employees"] == 2
    assert gaps["TEST_A"]["average_gap"] == 5
    assert gaps["TEST_MISSING"]["skill_name"] == "Planning"
    assert gaps["TEST_MISSING"]["average_gap"] == 4
    assert result["popular_events"] == [{"event_id": "EV_005", "count": 2}]


def explanation(event_id):
    return {
        "event_id": event_id, "explanation": "A verified skill gap.",
        "employee_friendly_reason": "Build your next skill.",
        "risk_note": "Check prerequisites.", "expected_outcome": "Practice the relevant skill.",
    }


def mock_agent_response(monkeypatch, raw):
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(raw).encode()

    def urlopen(req, **_kwargs):
        captured.append(json.loads(req.data))
        return Response()

    monkeypatch.setattr(llm_service.settings, "openai_api_key", "test-key-never-sent")
    monkeypatch.setattr(llm_service.request, "urlopen", urlopen)
    return captured


@pytest.mark.parametrize("parsed", [
    None, [], {},
    {"summary": "", "recommendation_explanations": [explanation("A")]},
    {"summary": [], "recommendation_explanations": [explanation("A")]},
    {"summary": "Summary", "recommendation_explanations": []},
    {"summary": "Summary", "recommendation_explanations": [None]},
    {"summary": "Summary", "recommendation_explanations": [{"event_id": "A"}]},
    {"summary": "Summary", "recommendation_explanations": [explanation("UNKNOWN")]},
    {"summary": "Summary", "recommendation_explanations": [{**explanation("A"), "risk_note": " "}]},
    {"summary": "Summary", "recommendation_explanations": [{**explanation("A"), "score": 999}]},
    {"summary": "Summary", "recommendation_explanations": [explanation("A")], "provider": "invented"},
])
def test_invalid_agent_output_falls_back_to_deterministic_explanation(monkeypatch, parsed):
    mock_agent_response(monkeypatch, {"output_text": json.dumps(parsed)})
    result = llm_service.explain_recommendations({}, [{"event_id": "A", "explanation": "Verified baseline"}])
    assert result["provider"] == "template"
    assert result["recommendation_explanations"][0]["explanation"] == "Verified baseline"


@pytest.mark.parametrize("raw", [
    [], {"output": [None]}, {"output": [{"content": [None]}]},
    {"output": [{"content": [{"type": "refusal", "refusal": "Unavailable"}]}]},
    {"status": "incomplete", "output_text": json.dumps({"summary": "Summary", "recommendation_explanations": [explanation("A")]})},
])
def test_malformed_or_incomplete_agent_envelope_falls_back(monkeypatch, raw):
    mock_agent_response(monkeypatch, raw)
    result = llm_service.explain_recommendations({}, [{"event_id": "A"}])
    assert result["provider"] == "template"


def test_valid_agent_output_preserves_candidate_order_and_requested_language(monkeypatch):
    parsed = {"summary": "Summary", "recommendation_explanations": [explanation("B"), explanation("A")]}
    captured = mock_agent_response(monkeypatch, {
        "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(parsed)}]}],
    })
    candidates = [{"event_id": "A", "score": 42}, {"event_id": "B", "score": 10}]
    result = llm_service.explain_recommendations({"language": "kk"}, candidates)
    assert result["provider"] == "openai"
    assert [item["event_id"] for item in result["recommendation_explanations"]] == ["A", "B"]
    assert candidates == [{"event_id": "A", "score": 42}, {"event_id": "B", "score": 10}]
    assert "Kazakh" in captured[0]["input"][0]["content"]
    schema = captured[0]["text"]["format"]
    assert schema["strict"] is True
    assert schema["schema"]["properties"]["recommendation_explanations"]["items"]["properties"]["event_id"]["enum"] == ["A", "B"]


@pytest.mark.parametrize("ids", [["A"], ["A", "A"]])
def test_partial_and_duplicate_agent_recommendations_fall_back(monkeypatch, ids):
    mock_agent_response(monkeypatch, {"output_text": json.dumps({
        "summary": "Summary", "recommendation_explanations": [explanation(event_id) for event_id in ids],
    })})
    result = llm_service.explain_recommendations({}, [{"event_id": "A"}, {"event_id": "B"}])
    assert result["provider"] == "template"
    assert [item["event_id"] for item in result["recommendation_explanations"]] == ["A", "B"]
