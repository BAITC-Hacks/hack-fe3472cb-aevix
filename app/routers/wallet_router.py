from typing import Any

from fastapi import APIRouter

from app.services.esg_service import get_wallet

router = APIRouter()


@router.get("/{employee_id}")
def wallet(employee_id: str) -> dict[str, Any]:
    return get_wallet(employee_id)
