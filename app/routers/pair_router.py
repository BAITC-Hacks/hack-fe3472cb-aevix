from typing import Any

from fastapi import APIRouter

from app.services.pair_service import create_invitation, get_pair_space, list_invitations, preview_invitation, respond_to_invitation

router = APIRouter()


@router.post("/invitations")
def publish_invitation(payload: dict[str, Any]) -> dict[str, Any]:
    return create_invitation(payload)


@router.get("/invitations")
def invitations(employee_id: str | None = None) -> list[dict[str, Any]]:
    return list_invitations(employee_id)


@router.post("/invitations/{invitation_id}/respond")
def respond(invitation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return respond_to_invitation(invitation_id, payload)


@router.get("/invitations/{invitation_id}/preview")
def preview(invitation_id: str, employee_id: str) -> dict[str, Any]:
    return preview_invitation(invitation_id, employee_id)


@router.get("/{pair_id}")
def pair_space(pair_id: str) -> dict[str, Any]:
    return get_pair_space(pair_id)
