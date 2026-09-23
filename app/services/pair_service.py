from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.db.database import SessionLocal
from app.db.models import Employee, Event, PairInvitation, PairSpace, QuestProgress
from app.services.recommendation_service import get_employee_recommendations

PAIR_FORMATS = {"online_together", "in_person", "self_paced_discussion"}
DISPLAY_MODES = {"name", "alias"}


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date: {value}") from exc


def _public_invitation(db, invitation: PairInvitation) -> dict[str, Any]:
    event = db.get(Event, invitation.event_id)
    return {
        "invitation_id": invitation.invitation_id,
        "event_id": invitation.event_id,
        "activity_title": event.title if event else invitation.event_id,
        "activity_type": event.type if event else None,
        "activity_format": invitation.format,
        "start_date": invitation.start_date.isoformat() if invitation.start_date else None,
        "end_date": invitation.end_date.isoformat() if invitation.end_date else None,
        "display_name": invitation.display_name,
        "display_mode": invitation.display_mode,
        "status": invitation.status,
    }


def create_invitation(payload: dict[str, Any]) -> dict[str, Any]:
    inviter_id = payload.get("inviter_id")
    event_id = payload.get("event_id")
    collaboration_format = payload.get("format")
    display_mode = payload.get("display_mode", "name")
    db = SessionLocal()
    try:
        inviter = db.get(Employee, inviter_id)
        event = db.get(Event, event_id)
        if not inviter:
            raise HTTPException(status_code=404, detail="Inviting employee not found")
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.mandatory:
            raise HTTPException(status_code=409, detail="Mandatory activities cannot be published as pair invitations")
        if collaboration_format not in PAIR_FORMATS:
            raise HTTPException(status_code=422, detail=f"format must be one of: {', '.join(sorted(PAIR_FORMATS))}")
        if display_mode not in DISPLAY_MODES:
            raise HTTPException(status_code=422, detail="display_mode must be name or alias")

        recommendations = get_employee_recommendations(inviter_id, use_llm=False)["recommendations"]
        selected = db.query(QuestProgress).filter_by(employee_id=inviter_id, event_id=event_id).first()
        if not any(item["event_id"] == event_id for item in recommendations) and not selected:
            raise HTTPException(status_code=409, detail="Activity must be selected or recommended for the inviting employee")

        display_name = payload.get("display_name") or inviter.full_name
        if display_mode == "alias":
            display_name = payload.get("display_name") or f"Colleague {inviter_id[-4:]}"
        invitation = PairInvitation(
            invitation_id=f"PAIR_INV_{uuid4().hex[:10]}",
            inviter_id=inviter_id,
            event_id=event_id,
            start_date=_parse_date(payload.get("start_date")),
            end_date=_parse_date(payload.get("end_date")),
            format=collaboration_format,
            display_mode=display_mode,
            display_name=display_name,
            status="open",
            created_at=date.today(),
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return _public_invitation(db, invitation)
    finally:
        db.close()


def list_invitations(employee_id: str | None = None) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        query = db.query(PairInvitation).filter_by(status="open")
        if employee_id:
            query = query.filter(PairInvitation.inviter_id != employee_id)
        return [_public_invitation(db, item) for item in query.order_by(PairInvitation.created_at.desc()).all()]
    finally:
        db.close()


def _candidate_match(db, invitation: PairInvitation, employee_id: str) -> dict[str, Any]:
    recommendations = get_employee_recommendations(employee_id, use_llm=False)["recommendations"]
    match = next((item for item in recommendations if item["event_id"] == invitation.event_id), None)
    if match:
        return {
            "eligible": True,
            "event_id": invitation.event_id,
            "explanation": match["explanation"],
            "employee_friendly_reason": match.get("reason", match["explanation"]),
        }
    return {
        "eligible": False,
        "event_id": invitation.event_id,
        "explanation": "This activity is not currently a suitable development step for your role, target grade, or skill gaps.",
        "employee_friendly_reason": "We did not present this as a successful match because it does not currently support your development path.",
    }


def respond_to_invitation(invitation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    employee_id = payload.get("employee_id")
    decision = payload.get("decision", "accept")
    db = SessionLocal()
    try:
        invitation = db.get(PairInvitation, invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Pair invitation not found")
        if invitation.status != "open":
            raise HTTPException(status_code=409, detail="Pair invitation is no longer open")
        if employee_id == invitation.inviter_id:
            raise HTTPException(status_code=422, detail="Inviter cannot respond to own invitation")
        if not db.get(Employee, employee_id):
            raise HTTPException(status_code=404, detail="Responding employee not found")
        if decision == "decline":
            invitation.status = "declined"
            db.commit()
            return {"invitation_id": invitation_id, "status": "declined", "eligible": False}
        if decision != "accept":
            raise HTTPException(status_code=422, detail="decision must be accept or decline")

        match = _candidate_match(db, invitation, employee_id)
        if not match["eligible"]:
            return {"invitation_id": invitation_id, "status": "not_a_match", **match}
        invitation.status = "accepted"
        pair = PairSpace(
            pair_id=f"PAIR_{uuid4().hex[:10]}",
            invitation_id=invitation.invitation_id,
            event_id=invitation.event_id,
            inviter_id=invitation.inviter_id,
            partner_id=employee_id,
            status="active",
            created_at=date.today(),
        )
        db.add(pair)
        db.commit()
        return {
            "invitation_id": invitation_id,
            "pair_id": pair.pair_id,
            "status": "accepted",
            "eligible": True,
            "event_id": invitation.event_id,
            "activity_title": db.get(Event, invitation.event_id).title,
            "next_step": "Open the pair space and agree on the first session.",
            "candidate_explanation": match["explanation"],
            "employee_friendly_reason": match["employee_friendly_reason"],
        }
    finally:
        db.close()


def preview_invitation(invitation_id: str, employee_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        invitation = db.get(PairInvitation, invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Pair invitation not found")
        if not db.get(Employee, employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")
        if employee_id == invitation.inviter_id:
            raise HTTPException(status_code=422, detail="Inviter cannot preview own invitation")
        match = _candidate_match(db, invitation, employee_id)
        return {
            "invitation_id": invitation_id,
            "event_id": invitation.event_id,
            "activity_title": db.get(Event, invitation.event_id).title,
            "eligible": match["eligible"],
            "explanation": match["explanation"],
            "employee_friendly_reason": match["employee_friendly_reason"],
            "can_respond": match["eligible"] and invitation.status == "open",
        }
    finally:
        db.close()


def get_pair_space(pair_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        pair = db.get(PairSpace, pair_id)
        if not pair:
            raise HTTPException(status_code=404, detail="Pair space not found")
        event = db.get(Event, pair.event_id)
        return {
            "pair_id": pair.pair_id,
            "status": pair.status,
            "event_id": pair.event_id,
            "activity_title": event.title if event else pair.event_id,
            "members": [pair.inviter_id, pair.partner_id],
            "next_step": "Agree on a start date and complete the activity together.",
            "messages": [],
        }
    finally:
        db.close()
