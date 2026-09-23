from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, PairInvitation, PairInvitationDismissal, PairSpace, QuestProgress
from app.schemas.collaboration import PairInvitationCreate, PairInvitationResponse
from app.services.quest_service import quest_write_transaction
from app.services.recommendation_service import get_employee_recommendations


def _public_invitation(db: Session, invitation: PairInvitation) -> dict[str, Any]:
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


def _recommendations(db: Session, employee_id: str) -> list[dict[str, Any]]:
    # Suitability must not depend on whether an activity fits into the top three.
    return get_employee_recommendations(
        employee_id, limit=max(db.query(Event).count(), 1), use_llm=False,
    )["recommendations"]


def _is_completed(db: Session, employee_id: str, event_id: str) -> bool:
    return (
        db.query(ActivityHistory).filter_by(employee_id=employee_id, event_id=event_id, status="completed").first() is not None
        or db.query(QuestProgress).filter_by(employee_id=employee_id, event_id=event_id, status="completed").first() is not None
    )


def create_invitation(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = PairInvitationCreate.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with quest_write_transaction() as db:
        inviter = db.get(Employee, request.inviter_id)
        event = db.get(Event, request.event_id)
        if not inviter:
            raise HTTPException(status_code=404, detail="Inviting employee not found")
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.mandatory:
            raise HTTPException(status_code=409, detail="Mandatory activities cannot be published as pair invitations")
        if _is_completed(db, request.inviter_id, request.event_id):
            raise HTTPException(status_code=409, detail="Completed activities cannot be published as pair invitations")
        selected = db.query(QuestProgress).filter_by(employee_id=request.inviter_id, event_id=request.event_id).filter(
            QuestProgress.status.in_(["selected", "in_progress"]),
        ).first()
        if not selected and not any(item["event_id"] == request.event_id for item in _recommendations(db, request.inviter_id)):
            raise HTTPException(status_code=409, detail="Activity must be selected or recommended for the inviting employee")

        display_name = request.display_name or inviter.full_name
        if request.display_mode == "alias":
            display_name = request.display_name or f"Colleague {request.inviter_id[-4:]}"
        invitation = PairInvitation(
            invitation_id=f"PAIR_INV_{uuid4().hex[:10]}",
            inviter_id=request.inviter_id,
            event_id=request.event_id,
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            display_mode=request.display_mode,
            display_name=display_name,
            status="open",
            created_at=date.today(),
        )
        db.add(invitation)
        db.flush()
        return _public_invitation(db, invitation)


def list_invitations(employee_id: str | None = None, own: bool = False) -> list[dict[str, Any]]:
    if own and employee_id is None:
        raise HTTPException(status_code=422, detail="employee_id is required for authored invitations")
    with SessionLocal() as db:
        query = db.query(PairInvitation).filter_by(status="open")
        if employee_id is not None:
            if not db.get(Employee, employee_id):
                raise HTTPException(status_code=404, detail="Employee not found")
            if own:
                query = query.filter(PairInvitation.inviter_id == employee_id)
            else:
                dismissed = select(PairInvitationDismissal.invitation_id).where(
                    PairInvitationDismissal.employee_id == employee_id,
                )
                query = query.filter(PairInvitation.inviter_id != employee_id, ~PairInvitation.invitation_id.in_(dismissed))
        return [_public_invitation(db, item) for item in query.order_by(PairInvitation.created_at.desc(), PairInvitation.invitation_id).all()]


def _candidate_match(db: Session, invitation: PairInvitation, employee_id: str) -> dict[str, Any]:
    recommendations = _recommendations(db, employee_id)
    event = db.get(Event, invitation.event_id)
    match = next((item for item in recommendations if item["event_id"] == invitation.event_id), None)
    if event and not event.mandatory and match and not _is_completed(db, employee_id, invitation.event_id):
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
    try:
        request = PairInvitationResponse.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with quest_write_transaction() as db:
        invitation = db.get(PairInvitation, invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Pair invitation not found")
        if invitation.status != "open":
            raise HTTPException(status_code=409, detail="Pair invitation is no longer open")
        if request.employee_id == invitation.inviter_id:
            raise HTTPException(status_code=422, detail="Inviter cannot respond to own invitation")
        if not db.get(Employee, request.employee_id):
            raise HTTPException(status_code=404, detail="Responding employee not found")
        dismissal = db.get(PairInvitationDismissal, (invitation_id, request.employee_id))
        if request.decision == "decline":
            if dismissal is None:
                db.add(PairInvitationDismissal(invitation_id=invitation_id, employee_id=request.employee_id))
            return {"invitation_id": invitation_id, "status": "declined", "eligible": False}
        if dismissal is not None:
            raise HTTPException(status_code=409, detail="Invitation was dismissed for this employee")

        event = db.get(Event, invitation.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if _is_completed(db, invitation.inviter_id, invitation.event_id):
            raise HTTPException(status_code=409, detail="Inviting employee has already completed this activity")
        match = _candidate_match(db, invitation, request.employee_id)
        if not match["eligible"]:
            return {"invitation_id": invitation_id, "status": "not_a_match", **match}
        invitation.status = "accepted"
        pair = PairSpace(
            pair_id=f"PAIR_{uuid4().hex[:10]}",
            invitation_id=invitation.invitation_id,
            event_id=invitation.event_id,
            inviter_id=invitation.inviter_id,
            partner_id=request.employee_id,
            status="active",
            created_at=date.today(),
        )
        db.add(pair)
        db.flush()
        return {
            "invitation_id": invitation_id,
            "pair_id": pair.pair_id,
            "status": "accepted",
            "eligible": True,
            "event_id": invitation.event_id,
            "activity_title": event.title,
            "next_step": "Open the pair space and agree on the first session.",
            "candidate_explanation": match["explanation"],
            "employee_friendly_reason": match["employee_friendly_reason"],
        }


def preview_invitation(invitation_id: str, employee_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        invitation = db.get(PairInvitation, invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Pair invitation not found")
        if not db.get(Employee, employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")
        if employee_id == invitation.inviter_id:
            raise HTTPException(status_code=422, detail="Inviter cannot preview own invitation")
        event = db.get(Event, invitation.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        match = _candidate_match(db, invitation, employee_id)
        dismissed = db.get(PairInvitationDismissal, (invitation_id, employee_id)) is not None
        return {
            "invitation_id": invitation_id,
            "event_id": invitation.event_id,
            "activity_title": event.title,
            "eligible": match["eligible"],
            "explanation": match["explanation"],
            "employee_friendly_reason": match["employee_friendly_reason"],
            "dismissed": dismissed,
            "can_respond": match["eligible"] and not dismissed and invitation.status == "open" and not _is_completed(db, invitation.inviter_id, invitation.event_id),
        }


def get_pair_space(pair_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
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
