"""Collaboration identity boundaries through real cookie and password sessions."""
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from app.db.database import SessionLocal
from app.db.models import CoinTransaction, Employee, Event, PairInvitation, PairSpace, QuestProgress, Team, Wallet
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as browser:
        yield browser


@pytest.fixture
def spaces(client, employee_sign_in):
    """Two members create both spaces; a second invitation remains available."""
    with SessionLocal() as db:
        original = db.get(Employee, "E0002")
        db.add(Employee(
            employee_id="AUTH_PARTNER", full_name="Collaboration partner",
            role=original.role, grade=original.grade,
            career_goal=deepcopy(original.career_goal), skills=deepcopy(original.skills),
        ))
        db.add(Event(event_id="AUTH_TEAM_EVENT", title="Shared activity", mandatory=False))
        db.commit()
    employee_sign_in(client, "E0002")
    response = client.post("/api/teams", json={"creator_id": "E0002", "name": "Members only", "max_members": 5})
    assert response.status_code == 200, response.text
    team_id = response.json()["team_id"]
    invitation_payload = {
        "inviter_id": "E0002", "event_id": "EV_005", "format": "online_together",
        "display_mode": "alias", "display_name": "A colleague",
    }
    invitation = client.post("/api/pairs/invitations", json=invitation_payload)
    assert invitation.status_code == 200, invitation.text
    employee_sign_in(client, "AUTH_PARTNER")
    assert client.post(f"/api/teams/{team_id}/join", json={"employee_id": "AUTH_PARTNER"}).status_code == 200
    accepted = client.post(
        f"/api/pairs/invitations/{invitation.json()['invitation_id']}/respond", json={"employee_id": "AUTH_PARTNER"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    employee_sign_in(client, "E0002")
    invitation = client.post("/api/pairs/invitations", json=invitation_payload)
    assert invitation.status_code == 200, invitation.text
    return {
        "team_id": team_id, "pair_id": accepted.json()["pair_id"],
        "invitation_id": invitation.json()["invitation_id"], "event_id": "AUTH_TEAM_EVENT",
    }


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/api/teams", None),
    ("get", "/api/teams?employee_id=E0002", None),
    ("get", "/api/teams/unknown", None),
    ("post", "/api/teams", {"creator_id": "E0002"}),
    ("post", "/api/teams/unknown/join", {"employee_id": "E0002"}),
    ("post", "/api/teams/unknown/pause", None),
    ("post", "/api/teams/unknown/resume", None),
    ("post", "/api/teams/unknown/quests/EV_005/start", None),
    ("post", "/api/teams/unknown/quests/EV_005/complete", None),
    ("get", "/api/pairs", None),
    ("get", "/api/pairs?employee_id=E0002", None),
    ("get", "/api/pairs/unknown", None),
    ("get", "/api/pairs/invitations", None),
    ("get", "/api/pairs/invitations/unknown/preview?employee_id=E0002", None),
    ("post", "/api/pairs/invitations", {"inviter_id": "E0002", "event_id": "EV_005", "format": "in_person"}),
    ("post", "/api/pairs/invitations/unknown/respond", {"employee_id": "E0002"}),
])
def test_every_collaboration_route_requires_a_session(client, method, path, payload):
    response = client.request(method, path, **({"json": payload} if payload is not None else {}))
    assert response.status_code == 401, response.text


def test_employee_cannot_forge_actor_or_personal_query_ids(client, spaces):
    team_id, invitation_id = spaces["team_id"], spaces["invitation_id"]
    writes = [
        ("/api/teams", {"creator_id": "E0001", "name": "Forged team"}),
        (f"/api/teams/{team_id}/join", {"employee_id": "E0001"}),
        ("/api/pairs/invitations", {"inviter_id": "E0001", "event_id": "EV_005", "format": "in_person"}),
        (f"/api/pairs/invitations/{invitation_id}/respond", {"employee_id": "AUTH_PARTNER"}),
        (f"/api/pairs/invitations/{invitation_id}/respond", {"employee_id": "AUTH_PARTNER", "decision": "decline"}),
    ]
    for path, payload in writes:
        response = client.post(path, json=payload)
        assert response.status_code == 403, (path, response.text)
    for path in ["/api/teams", "/api/pairs", "/api/pairs/invitations", f"/api/pairs/invitations/{invitation_id}/preview"]:
        for foreign_id in ("AUTH_PARTNER", "MISSING"):
            response = client.get(path, params={"employee_id": foreign_id})
            assert response.status_code == 403, (path, response.text)
    assert client.get(f"/api/teams/{team_id}").json()["member_ids"] == ["E0002", "AUTH_PARTNER"]
    with SessionLocal() as db:
        assert db.query(Team).count() == 1
        assert db.query(PairSpace).count() == 1
        assert db.query(PairInvitation).count() == 2
        assert db.get(PairInvitation, invitation_id).status == "open"


def test_nonmember_cannot_read_or_operate_private_spaces(client, spaces, employee_sign_in):
    employee_sign_in(client, "E0001")
    base = f"/api/teams/{spaces['team_id']}"
    assert client.get(base).status_code == 403
    assert client.get(f"/api/pairs/{spaces['pair_id']}").status_code == 403
    for path in [f"{base}/pause", f"{base}/resume", f"{base}/quests/{spaces['event_id']}/start", f"{base}/quests/{spaces['event_id']}/complete"]:
        response = client.post(path)
        assert response.status_code == 403, (path, response.text)
    assert client.get("/api/teams").json() == []
    assert client.get("/api/pairs").json() == []
    employee_sign_in(client, "E0002")
    team = client.get(base).json()
    assert team["status"] == "active"
    assert team["current_quest"] is None
    assert team["completed_team_quests"] == 0


def test_code_join_adds_only_the_signed_in_employee(client, spaces, employee_sign_in):
    employee_sign_in(client, "E0001")
    base = f"/api/teams/{spaces['team_id']}"
    assert client.get(base).status_code == 403
    assert client.post(f"{base}/join", json={"employee_id": "E0003"}).status_code == 403
    joined = client.post(f"{base}/join", json={"employee_id": "E0001"})
    assert joined.status_code == 200, joined.text
    assert joined.json()["member_ids"] == ["E0002", "AUTH_PARTNER", "E0001"]
    assert client.get(base).status_code == 200
    assert [team["team_id"] for team in client.get("/api/teams").json()] == [spaces["team_id"]]
    assert client.post(f"{base}/pause").json()["status"] == "paused"
    assert client.post(f"{base}/resume").json()["status"] == "active"


def test_hr_can_preview_spaces_but_cannot_mutate_employees(client, spaces, hr_sign_in):
    hr_sign_in(client)
    base = f"/api/teams/{spaces['team_id']}"
    team_before = client.get(base).json()
    pair_before = client.get(f"/api/pairs/{spaces['pair_id']}").json()
    assert team_before["member_ids"] == pair_before["members"] == ["E0002", "AUTH_PARTNER"]
    for employee_id in ("E0002", "AUTH_PARTNER"):
        assert [row["team_id"] for row in client.get("/api/teams", params={"employee_id": employee_id}).json()] == [spaces["team_id"]]
        assert [row["pair_id"] for row in client.get("/api/pairs", params={"employee_id": employee_id}).json()] == [spaces["pair_id"]]
    assert client.get(f"/api/pairs/invitations/{spaces['invitation_id']}/preview", params={"employee_id": "AUTH_PARTNER"}).status_code == 200
    writes = [
        ("/api/teams", {"creator_id": "E0002"}),
        (f"{base}/join", {"employee_id": "E0001"}),
        (f"{base}/pause", None),
        (f"{base}/resume", None),
        (f"{base}/quests/{spaces['event_id']}/start", None),
        (f"{base}/quests/{spaces['event_id']}/complete", None),
        ("/api/pairs/invitations", {"inviter_id": "E0002", "event_id": "EV_005", "format": "in_person"}),
        (f"/api/pairs/invitations/{spaces['invitation_id']}/respond", {"employee_id": "AUTH_PARTNER"}),
        (f"/api/pairs/invitations/{spaces['invitation_id']}/respond", {"employee_id": "AUTH_PARTNER", "decision": "decline"}),
    ]
    for path, payload in writes:
        response = client.post(path, **({"json": payload} if payload is not None else {}))
        assert response.status_code == 403, (path, response.text)
    assert client.get(base).json() == team_before
    assert client.get(f"/api/pairs/{spaces['pair_id']}").json() == pair_before
    with SessionLocal() as db:
        assert db.query(Team).count() == 1
        assert db.query(PairSpace).count() == 1
        assert db.query(PairInvitation).count() == 2
        assert db.get(PairInvitation, spaces["invitation_id"]).status == "open"


def test_member_lists_restore_in_a_fresh_browser_without_saved_codes(client, spaces, employee_sign_in):
    employee_sign_in(client, "E0003")
    other = client.post("/api/teams", json={"creator_id": "E0003", "name": "Another team"})
    assert other.status_code == 200, other.text
    with TestClient(app) as fresh_browser:
        assert fresh_browser.get("/api/teams").status_code == 401
        assert fresh_browser.get("/api/pairs").status_code == 401
        employee_sign_in(fresh_browser, "AUTH_PARTNER")
        for params in ({}, {"employee_id": "AUTH_PARTNER"}):
            teams = fresh_browser.get("/api/teams", params=params)
            pairs = fresh_browser.get("/api/pairs", params=params)
            assert teams.status_code == pairs.status_code == 200
            assert [team["team_id"] for team in teams.json()] == [spaces["team_id"]]
            assert [pair["pair_id"] for pair in pairs.json()] == [spaces["pair_id"]]
        assert fresh_browser.get(f"/api/teams/{other.json()['team_id']}").status_code == 403
        assert fresh_browser.get(f"/api/teams/{spaces['team_id']}").status_code == 200
        assert fresh_browser.get(f"/api/pairs/{spaces['pair_id']}").status_code == 200


def test_authenticated_public_feed_keeps_private_context_hidden(client, spaces, employee_sign_in):
    employee_sign_in(client, "E0001")
    for params in ({}, {"employee_id": "E0001"}):
        response = client.get("/api/pairs/invitations", params=params)
        assert response.status_code == 200
        assert len(response.json()) == 1
        invitation = response.json()[0]
        assert invitation["invitation_id"] == spaces["invitation_id"]
        assert invitation["display_name"] == "A colleague"
        assert not {"inviter_id", "skill_gaps", "skills", "score", "career_goal"}.intersection(invitation)
    assert client.get("/api/pairs/invitations", params={"employee_id": "E0002"}).status_code == 403


def test_team_mutations_require_csrf_from_the_same_session(client, spaces, employee_sign_in):
    base = f"/api/teams/{spaces['team_id']}"
    original_token = client.headers.pop("X-CSRF-Token")
    assert client.post(f"{base}/pause").status_code == 403
    with TestClient(app) as other_browser:
        employee_sign_in(other_browser, "AUTH_PARTNER")
        assert client.post(f"{base}/pause", headers={"X-CSRF-Token": other_browser.headers["X-CSRF-Token"]}).status_code == 403
    assert client.get(base).json()["status"] == "active"
    assert client.post(f"{base}/pause", headers={"X-CSRF-Token": original_token}).json()["status"] == "paused"


def test_team_completion_rewards_every_member_without_exposing_colleague_results(client, spaces):
    balances = {"E0002": 11, "AUTH_PARTNER": 9097}
    skill_levels = {"E0002": 1, "AUTH_PARTNER": 3}
    event_id = spaces["event_id"]
    with SessionLocal() as db:
        event = db.get(Event, event_id)
        event.duration_hours = 1
        event.develops_skills = [{"skill_id": "AUTH_PRIVATE_SKILL", "gain": 1, "max_level": 5}]
        for employee_id, balance in balances.items():
            db.merge(Wallet(employee_id=employee_id, balance=balance))
            employee = db.get(Employee, employee_id)
            employee.skills = {**employee.skills, "AUTH_PRIVATE_SKILL": skill_levels[employee_id]}
        db.commit()
    base = f"/api/teams/{spaces['team_id']}/quests/{event_id}"
    started = client.post(f"{base}/start")
    assert started.status_code == 200, started.text
    completed = client.post(f"{base}/complete")
    assert completed.status_code == 200, completed.text
    result = completed.json()
    assert result["completed_member_count"] == 2
    assert result["member_ids"] == ["E0002", "AUTH_PARTNER"]
    assert [member["employee_id"] for member in result["member_results"]] == ["E0002"]
    personal_result = result["member_results"][0]
    assert personal_result["updated_skills"]["AUTH_PRIVATE_SKILL"]["before"] == 1
    assert personal_result["updated_skills"]["AUTH_PRIVATE_SKILL"]["after"] == 2

    private_keys = {"wallet_balance", "updated_skills", "progress_to_next_grade_before", "progress_to_next_grade_after"}

    def private_records(value):
        if isinstance(value, dict):
            if private_keys.intersection(value):
                yield value
            for item in value.values():
                yield from private_records(item)
        elif isinstance(value, list):
            for item in value:
                yield from private_records(item)

    assert list(private_records(result)) == [personal_result]
    with SessionLocal() as db:
        rewards = db.query(CoinTransaction).filter_by(event_id=event_id).all()
        assert {reward.employee_id for reward in rewards} == set(balances)
        assert len(rewards) == 2
        for reward in rewards:
            assert reward.amount > 0
            assert db.get(Wallet, reward.employee_id).balance == balances[reward.employee_id] + reward.amount
            assert db.get(Employee, reward.employee_id).skills["AUTH_PRIVATE_SKILL"] == skill_levels[reward.employee_id] + 1
            assert db.query(QuestProgress).filter_by(employee_id=reward.employee_id, event_id=event_id).one().status == "completed"
        assert personal_result["wallet_balance"] == db.get(Wallet, "E0002").balance
