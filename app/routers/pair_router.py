from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_

from app.db.auth_models import AuthSession
from app.db.database import SessionLocal
from app.db.models import PairSpace
from app.services.auth_service import assert_employee_access, require_session

from app.schemas.collaboration import PairInvitationCreate, PairInvitationResponse
from app.services.pair_service import create_invitation, get_pair_space, list_invitations, preview_invitation, respond_to_invitation

router = APIRouter(dependencies=[Depends(require_session)])


@router.get("")
def pairs(employee_id: str | None = None, session: AuthSession = Depends(require_session)) -> list[dict[str, Any]]:
    employee_id = employee_id or session.employee_id
    if not employee_id:
        return []
    assert_employee_access(session, employee_id)
    with SessionLocal() as db:
        pair_ids = [row.pair_id for row in db.query(PairSpace).filter(or_(PairSpace.inviter_id == employee_id, PairSpace.partner_id == employee_id)).all()]
    return [get_pair_space(pair_id) for pair_id in pair_ids]


@router.post("/invitations")
def publish_invitation(payload: PairInvitationCreate, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    assert_employee_access(session, payload.inviter_id, allow_hr=False)
    return create_invitation(payload.model_dump())


@router.get("/invitations")
def invitations(
    employee_id: str | None = None, own: bool = False,
    session: AuthSession = Depends(require_session),
) -> list[dict[str, Any]]:
    employee_id = employee_id or session.employee_id
    if employee_id is not None:
        assert_employee_access(session, employee_id)
    return list_invitations(employee_id, own=own)


@router.post("/invitations/{invitation_id}/respond")
def respond(invitation_id: str, payload: PairInvitationResponse, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    assert_employee_access(session, payload.employee_id, allow_hr=False)
    return respond_to_invitation(invitation_id, payload.model_dump())


@router.get("/invitations/{invitation_id}/preview")
def preview(invitation_id: str, employee_id: str, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    assert_employee_access(session, employee_id)
    return preview_invitation(invitation_id, employee_id)


@router.get("/{pair_id}")
def pair_space(pair_id: str, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    pair = get_pair_space(pair_id)
    if session.role != "hr" and session.employee_id not in pair["members"]:
        raise HTTPException(403, "Pair access is limited to its members")
    return pair
