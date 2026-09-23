from fastapi import APIRouter, Depends

from app.services.auth_service import require_employee_access
from app.services.game_service import get_game_map, get_game_progress, get_game_quests

router = APIRouter(dependencies=[Depends(require_employee_access)])


@router.get("/{employee_id}/map")
def game_map(employee_id: str) -> dict:
    return get_game_map(employee_id)


@router.get("/{employee_id}/progress")
def game_progress(employee_id: str) -> dict:
    return get_game_progress(employee_id)


@router.get("/{employee_id}/quests")
def game_quests(employee_id: str) -> list[dict]:
    return get_game_quests(employee_id)
