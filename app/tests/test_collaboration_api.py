"""HTTP collaboration workflows and transaction regressions on the isolated DB."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, CoinTransaction, Employee, Event, PairSpace, QuestProgress
from app.main import app
from app.services.pair_service import respond_to_invitation
from app.services.recommendation_service import complete_quest, get_employee_recommendations


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def team_events():
    with SessionLocal() as db:
        db.add_all([
            Event(event_id=f"COLL_TEAM_{index}", title=f"Team activity {index}", duration_hours=1, mandatory=False)
            for index in range(4)
        ])
        db.commit()
    return [f"COLL_TEAM_{index}" for index in range(4)]


@pytest.fixture
def pair_employees():
    with SessionLocal() as db:
        original = db.get(Employee, "E0002")
        for employee_id in ("COLL_PARTNER", "COLL_PARTNER_2"):
            db.add(Employee(
                employee_id=employee_id, full_name=employee_id, role=original.role, grade=original.grade,
                career_goal=deepcopy(original.career_goal), skills=deepcopy(original.skills),
            ))
        db.add(Employee(employee_id="COLL_UNSUITABLE", full_name="Different role", role="Unrelated", grade="Junior", skills={}))
        db.commit()
    return "COLL_PARTNER", "COLL_PARTNER_2"


def _team(client, max_members=5):
    response = client.post("/api/teams", json={"creator_id": "E0002", "name": "API team", "max_members": max_members})
    assert response.status_code == 200, response.text
    team_id = response.json()["team_id"]
    response = client.post(f"/api/teams/{team_id}/join", json={"employee_id": "E0001"})
    assert response.status_code == 200, response.text
    return team_id


def _invitation(client, event_id="EV_005"):
    response = client.post("/api/pairs/invitations", json={
        "inviter_id": "E0002", "event_id": event_id, "format": "online_together",
        "start_date": "2026-10-01", "end_date": "2026-10-07", "display_mode": "alias", "display_name": "Colleague",
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_team_http_workflow_persists_quest_and_resumes_it(client, team_events):
    team_id = _team(client, max_members=2)
    base = f"/api/teams/{team_id}"
    assert client.get(base).json()["member_ids"] == ["E0002", "E0001"]
    assert client.post(f"{base}/join", json={"employee_id": "E0001"}).status_code == 200
    assert client.post(f"{base}/pause").json()["status"] == "paused"
    assert client.post(f"{base}/resume").json()["status"] == "active"
    started = client.post(f"{base}/quests/{team_events[0]}/start")
    assert started.status_code == 200, started.text
    assert client.get(base).json()["current_quest"] == started.json()["current_quest"]
    assert client.post(f"{base}/pause").json()["current_quest"]["status"] == "paused"
    assert client.post(f"{base}/quests/{team_events[0]}/complete").status_code == 409
    assert client.post(f"{base}/resume").json()["status"] == "in_progress"
    completed = client.post(f"{base}/quests/{team_events[0]}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["completed_team_quests"] == 1
    assert len(completed.json()["member_results"]) == 2
    assert completed.json()["current_quest"] is None
    assert client.post(f"{base}/quests/{team_events[0]}/complete").status_code == 409
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(event_id=team_events[0], status="completed").count() == 2
        assert db.query(QuestProgress).filter_by(event_id=team_events[0], mode="team", status="completed").count() == 2
        assert db.query(CoinTransaction).filter_by(event_id=team_events[0]).count() == 2


def test_team_rejects_invalid_states_and_capacity_without_mutation(client, team_events):
    team_id = _team(client, max_members=2)
    base = f"/api/teams/{team_id}"
    assert client.post(f"{base}/resume").status_code == 409
    assert client.post(f"{base}/quests/{team_events[0]}/complete").status_code == 409
    assert client.post(f"{base}/quests/MISSING/start").status_code == 404
    assert client.post(f"{base}/join", json={"employee_id": "E0003"}).status_code == 409
    assert client.post(f"{base}/join", json={"employee_id": "MISSING"}).status_code == 404
    assert client.post(f"{base}/quests/{team_events[0]}/start").status_code == 200
    assert client.post(f"{base}/quests/{team_events[1]}/start").status_code == 409
    assert client.post(f"{base}/quests/{team_events[1]}/complete").status_code == 409
    assert client.post(f"{base}/join", json={"employee_id": "E0003"}).status_code == 409
    assert client.get(base).json()["current_quest"]["event_id"] == team_events[0]
    assert client.get(base).json()["completed_team_quests"] == 0


def test_team_completion_failure_rolls_back_every_member(client, team_events):
    team_id = _team(client)
    base = f"/api/teams/{team_id}"
    assert client.post(f"{base}/quests/{team_events[0]}/start").status_code == 200
    complete_quest("E0001", team_events[0])
    assert client.post(f"{base}/quests/{team_events[0]}/complete").status_code == 409
    team = client.get(base).json()
    assert team["completed_team_quests"] == 0
    assert team["status"] == "in_progress"
    with SessionLocal() as db:
        assert db.query(ActivityHistory).filter_by(employee_id="E0002", event_id=team_events[0]).one().status == "in_progress"
        assert db.query(QuestProgress).filter_by(employee_id="E0002", event_id=team_events[0]).one().status == "selected"
        assert db.query(CoinTransaction).filter_by(employee_id="E0002", event_id=team_events[0]).count() == 0


def test_team_start_failure_rolls_back_earlier_member_selection(client):
    with SessionLocal() as db:
        employee = db.get(Employee, "E0002")
        employee.skills = {**employee.skills, "COLL_PREREQ": 1}
        db.add(Event(event_id="COLL_LOCKED", title="Locked team activity", prerequisites={"COLL_PREREQ": 1}, mandatory=False))
        db.commit()
    team_id = _team(client)
    assert client.post(f"/api/teams/{team_id}/quests/COLL_LOCKED/start").status_code == 409
    assert client.get(f"/api/teams/{team_id}").json()["status"] == "active"
    with SessionLocal() as db:
        assert db.query(QuestProgress).filter_by(event_id="COLL_LOCKED").count() == 0
        assert db.query(ActivityHistory).filter_by(event_id="COLL_LOCKED").count() == 0


@pytest.mark.parametrize("capacity,expected_status", [(3, "waiting_for_member"), (2, "active")])
def test_team_can_continue_after_three_quests(client, team_events, capacity, expected_status):
    team_id = _team(client, max_members=capacity)
    base = f"/api/teams/{team_id}"
    for event_id in team_events[:3]:
        assert client.post(f"{base}/quests/{event_id}/start").status_code == 200
        response = client.post(f"{base}/quests/{event_id}/complete")
        assert response.status_code == 200, response.text
    assert response.json()["status"] == expected_status
    if expected_status == "waiting_for_member":
        assert client.post(f"{base}/quests/{team_events[3]}/start").status_code == 409
        assert client.post(f"{base}/resume").status_code == 409
        assert client.post(f"{base}/join", json={"employee_id": "E0003"}).json()["status"] == "active"
    assert client.post(f"{base}/quests/{team_events[3]}/start").status_code == 200


@pytest.mark.parametrize("path,payload", [
    ("/api/teams", {}),
    ("/api/teams", {"creator_id": "E0002", "max_members": 0}),
    ("/api/teams", {"creator_id": "E0002", "max_members": "invalid"}),
    ("/api/teams", {"creator_id": "E0002", "name": "  "}),
    ("/api/teams/missing/join", {}),
    ("/api/pairs/invitations", {}),
    ("/api/pairs/invitations", {"inviter_id": "E0002", "event_id": "EV_005", "format": "invalid"}),
    ("/api/pairs/invitations", {"inviter_id": "E0002", "event_id": "EV_005", "format": "online_together", "start_date": "2026-10-07", "end_date": "2026-10-01"}),
    ("/api/pairs/invitations", {"inviter_id": "E0002", "event_id": "EV_005", "format": "online_together", "start_date": "invalid"}),
    ("/api/pairs/invitations/missing/respond", {}),
    ("/api/pairs/invitations/missing/respond", {"employee_id": "E0002", "decision": "invalid"}),
])
def test_collaboration_payload_validation_returns_422(client, path, payload):
    assert client.post(path, json=payload).status_code == 422


def test_pair_http_flow_checks_suitability_and_hides_private_context(client, pair_employees):
    invitation = _invitation(client)
    invitation_id = invitation["invitation_id"]
    base = f"/api/pairs/invitations/{invitation_id}"
    assert invitation["display_name"] == "Colleague"
    assert not {"score", "skill_gaps", "inviter_id"}.intersection(invitation)
    assert client.get("/api/pairs/invitations", params={"employee_id": "E0002"}).json() == []
    assert len(client.get("/api/pairs/invitations", params={"employee_id": pair_employees[0]}).json()) == 1
    assert client.get(f"{base}/preview", params={"employee_id": "E0002"}).status_code == 422
    preview = client.get(f"{base}/preview", params={"employee_id": pair_employees[0]}).json()
    assert preview["eligible"] is True and preview["can_respond"] is True
    assert not {"score", "skill_gaps"}.intersection(preview)
    unsuitable = client.post(f"{base}/respond", json={"employee_id": "COLL_UNSUITABLE"})
    assert unsuitable.status_code == 200 and unsuitable.json()["status"] == "not_a_match"
    with SessionLocal() as db:
        assert db.query(PairSpace).count() == 0
    accepted = client.post(f"{base}/respond", json={"employee_id": pair_employees[0]})
    assert accepted.status_code == 200, accepted.text
    pair = client.get(f"/api/pairs/{accepted.json()['pair_id']}")
    assert pair.status_code == 200
    assert pair.json()["members"] == ["E0002", pair_employees[0]]
    assert client.post(f"{base}/respond", json={"employee_id": pair_employees[1]}).status_code == 409
    assert client.get(f"{base}/preview", params={"employee_id": pair_employees[1]}).json()["can_respond"] is False
    assert client.get("/api/pairs/invitations").json() == []


def test_pair_suitability_includes_activities_beyond_top_three(client, pair_employees):
    with SessionLocal() as db:
        db.add_all([
            Event(event_id=f"COLL_PAIR_{index}", title=f"Further development {index}", mandatory=False,
                  develops_skills=[{"skill_id": "SK_SYSTEM_DESIGN", "gain": 1, "max_level": 5}])
            for index in range(6)
        ])
        db.commit()
    candidates = get_employee_recommendations("E0002", limit=100, use_llm=False)["recommendations"]
    candidate = next(item for item in candidates[3:] if item["event_id"].startswith("COLL_PAIR_"))
    invitation = _invitation(client, event_id=candidate["event_id"])
    response = client.get(f"/api/pairs/invitations/{invitation['invitation_id']}/preview", params={"employee_id": pair_employees[0]})
    assert response.status_code == 200 and response.json()["eligible"] is True


def test_pair_rejects_mandatory_completed_and_stale_activities(client, pair_employees):
    invitation = _invitation(client)
    with SessionLocal() as db:
        db.add(Event(event_id="COLL_MANDATORY", title="Mandatory course", mandatory=True))
        db.commit()
    response = client.post("/api/pairs/invitations", json={"inviter_id": "E0002", "event_id": "COLL_MANDATORY", "format": "in_person"})
    assert response.status_code == 409
    complete_quest("E0002", "EV_005")
    response = client.post("/api/pairs/invitations", json={"inviter_id": "E0002", "event_id": "EV_005", "format": "in_person"})
    assert response.status_code == 409
    base = f"/api/pairs/invitations/{invitation['invitation_id']}"
    assert client.get(f"{base}/preview", params={"employee_id": pair_employees[0]}).json()["can_respond"] is False
    assert client.post(f"{base}/respond", json={"employee_id": pair_employees[0]}).status_code == 409


def test_pair_decline_closes_invitation(client, pair_employees):
    invitation = _invitation(client)
    base = f"/api/pairs/invitations/{invitation['invitation_id']}"
    response = client.post(f"{base}/respond", json={"employee_id": pair_employees[0], "decision": "decline"})
    assert response.status_code == 200 and response.json()["status"] == "declined"
    assert client.post(f"{base}/respond", json={"employee_id": pair_employees[1]}).status_code == 409
    with SessionLocal() as db:
        assert db.query(PairSpace).count() == 0


def test_concurrent_pair_acceptance_creates_one_space(client, pair_employees):
    invitation = _invitation(client)

    def respond(employee_id):
        try:
            respond_to_invitation(invitation["invitation_id"], {"employee_id": employee_id})
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(respond, pair_employees)) == [200, 409]
    with SessionLocal() as db:
        assert db.query(PairSpace).filter_by(invitation_id=invitation["invitation_id"]).count() == 1


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/api/teams/missing", None),
    ("post", "/api/teams/missing/pause", None),
    ("post", "/api/teams/missing/resume", None),
    ("post", "/api/teams/missing/quests/EV_005/start", None),
    ("post", "/api/teams/missing/quests/EV_005/complete", None),
    ("post", "/api/teams/missing/join", {"employee_id": "E0002"}),
    ("get", "/api/pairs/missing", None),
    ("get", "/api/pairs/invitations/missing/preview?employee_id=E0002", None),
    ("post", "/api/pairs/invitations/missing/respond", {"employee_id": "E0002"}),
    ("get", "/api/pairs/invitations?employee_id=missing", None),
])
def test_collaboration_missing_resources_return_404(client, method, path, payload):
    response = client.request(method, path, **({"json": payload} if payload is not None else {}))
    assert response.status_code == 404


def test_team_completion_waits_for_existing_member_plan_and_remains_atomic(client, team_events):
    team_id = _team(client)
    event_id = team_events[0]
    base = f"/api/teams/{team_id}"
    assert client.post(f"{base}/quests/{event_id}/start").status_code == 200
    plan_path = f"/api/employees/E0001/quests/{event_id}/steps"
    plan = client.get(plan_path).json()
    assert plan["steps"] and not plan["can_complete"]
    response = client.post(f"{base}/quests/{event_id}/complete")
    assert response.status_code == 409
    assert client.get(base).json()["completed_team_quests"] == 0
    with SessionLocal() as db:
        assert db.query(CoinTransaction).filter_by(event_id=event_id).count() == 0
        assert db.query(ActivityHistory).filter_by(event_id=event_id, status="completed").count() == 0
    for step in plan["steps"]:
        assert client.post(f"{plan_path}/{step['step']}/complete").status_code == 200
    response = client.post(f"{base}/quests/{event_id}/complete")
    assert response.status_code == 200, response.text
    assert response.json()["completed_team_quests"] == 1
    assert len(response.json()["member_results"]) == 2
