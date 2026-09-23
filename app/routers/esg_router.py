from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.esg_service import contribute, engagement, list_goals

router = APIRouter()


class ContributionRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=100, pattern=r"\S", strict=True)
    coins: int = Field(gt=0, le=2_147_483_647, strict=True)


@router.get("")
def goals() -> list[dict[str, Any]]:
    return list_goals()


@router.post("/{goal_id}/contribute")
def contribute_to_goal(goal_id: str, payload: ContributionRequest) -> dict[str, Any]:
    return contribute(goal_id, payload.employee_id, payload.coins)

