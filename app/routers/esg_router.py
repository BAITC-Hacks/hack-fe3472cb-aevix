from typing import Any

from fastapi import APIRouter

from app.services.esg_service import contribute, engagement, list_goals

router = APIRouter()


@router.get("")
def goals() -> list[dict[str, Any]]:
    return list_goals()


@router.post("/{goal_id}/contribute")
def contribute_to_goal(goal_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return contribute(goal_id, payload["employee_id"], int(payload["coins"]))


