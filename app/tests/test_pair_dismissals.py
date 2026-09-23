"""A public invitation can be dismissed by one colleague without cancelling it."""
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.db.database import SessionLocal
from app.db.models import PairInvitation, PairInvitationDismissal, PairSpace
from app.main import app
from app.services.import_service import register_employee
from app.services.pair_service import create_invitation, list_invitations, preview_invitation, respond_to_invitation
from app.services.quest_service import select_quest


def invitation_with_candidates():
    for employee_id in ("PAIR_DECLINER", "PAIR_ACCEPTOR"):
        register_employee({
            "employee_id": employee_id, "full_name": employee_id,
            "role": "Backend Engineer", "grade": "Middle",
            "career_goal": {"target_role": "Backend Engineer", "target_grade": "Senior"},
            "skills": {"SK_SYSTEM_DESIGN": 1, "SK_API_DESIGN": 1},
        })
    select_quest("E0002", "EV_005")
    return create_invitation({
        "inviter_id": "E0002", "event_id": "EV_005",
        "format": "online_together", "display_mode": "alias", "display_name": "Study partner",
    })


def test_decline_hides_only_from_responder_and_another_colleague_can_accept():
    invitation_id = invitation_with_candidates()["invitation_id"]
    assert any(item["invitation_id"] == invitation_id for item in list_invitations("PAIR_DECLINER"))
    response = respond_to_invitation(invitation_id, {"employee_id": "PAIR_DECLINER", "decision": "decline"})
    assert response["status"] == "declined"
    assert list_invitations("PAIR_DECLINER") == []
    assert any(item["invitation_id"] == invitation_id for item in list_invitations("PAIR_ACCEPTOR"))
    assert any(item["invitation_id"] == invitation_id for item in list_invitations("E0002", own=True))
    with SessionLocal() as db:
        assert db.get(PairInvitation, invitation_id).status == "open"
        assert db.query(PairInvitationDismissal).count() == 1
    preview = preview_invitation(invitation_id, "PAIR_DECLINER")
    assert preview["dismissed"]
    assert not preview["can_respond"]
    assert preview_invitation(invitation_id, "PAIR_ACCEPTOR")["can_respond"]
    response = respond_to_invitation(invitation_id, {"employee_id": "PAIR_ACCEPTOR", "decision": "accept"})
    assert response["status"] == "accepted"
    with SessionLocal() as db:
        assert db.get(PairInvitation, invitation_id).status == "accepted"
        pair = db.query(PairSpace).one()
        assert pair.partner_id == "PAIR_ACCEPTOR"


def test_repeated_dismissal_is_idempotent_and_cannot_later_accept():
    invitation_id = invitation_with_candidates()["invitation_id"]
    for _ in range(2):
        assert respond_to_invitation(invitation_id, {"employee_id": "PAIR_DECLINER", "decision": "decline"})["status"] == "declined"
    with pytest.raises(HTTPException) as error:
        respond_to_invitation(invitation_id, {"employee_id": "PAIR_DECLINER", "decision": "accept"})
    assert error.value.status_code == 409
    with SessionLocal() as db:
        assert db.query(PairInvitationDismissal).count() == 1
        assert db.get(PairInvitation, invitation_id).status == "open"
        assert db.query(PairSpace).count() == 0


def test_own_feed_is_bound_to_session_and_does_not_misclassify_dismissed_invites(employee_sign_in, hr_sign_in):
    invitation_id = invitation_with_candidates()["invitation_id"]
    with TestClient(app) as decliner:
        employee_sign_in(decliner, "PAIR_DECLINER")
        assert any(item["invitation_id"] == invitation_id for item in decliner.get("/api/pairs/invitations").json())
        assert decliner.post(f"/api/pairs/invitations/{invitation_id}/respond", json={
            "employee_id": "PAIR_DECLINER", "decision": "decline",
        }).status_code == 200
        assert decliner.get("/api/pairs/invitations").json() == []
        assert decliner.get("/api/pairs/invitations", params={"own": "true"}).json() == []
        assert decliner.get("/api/pairs/invitations", params={"employee_id": "E0002", "own": "true"}).status_code == 403
    with TestClient(app) as author:
        employee_sign_in(author, "E0002")
        own = author.get("/api/pairs/invitations", params={"own": "true"})
        assert own.status_code == 200
        assert [item["invitation_id"] for item in own.json()] == [invitation_id]
    with TestClient(app) as hr:
        hr_sign_in(hr)
        assert hr.get("/api/pairs/invitations", params={"own": "true"}).status_code == 422
        assert hr.get("/api/pairs/invitations", params={"employee_id": "E0002", "own": "true"}).status_code == 200
