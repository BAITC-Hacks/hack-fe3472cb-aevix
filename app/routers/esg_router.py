from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.esg_service import contribute, list_goals
from app.db.auth_models import AuthSession
from app.services.auth_service import assert_employee_access, require_session

router = APIRouter(dependencies=[Depends(require_session)])


class ContributionRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=100, pattern=r"\S", strict=True)
    coins: int = Field(gt=0, le=2_147_483_647, strict=True)


@router.get("")
def goals() -> list[dict[str, Any]]:
    return list_goals()


@router.post("/{goal_id}/contribute")
def contribute_to_goal(goal_id: str, payload: ContributionRequest, session: AuthSession = Depends(require_session)) -> dict[str, Any]:
    assert_employee_access(session, payload.employee_id, allow_hr=False)
    return contribute(goal_id, payload.employee_id, payload.coins)
