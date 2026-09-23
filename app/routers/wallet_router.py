from typing import Any

from fastapi import APIRouter, Depends

from app.services.auth_service import require_employee_access
from app.services.esg_service import get_wallet

router = APIRouter(dependencies=[Depends(require_employee_access)])


@router.get("/{employee_id}")
def wallet(employee_id: str) -> dict[str, Any]:
    return get_wallet(employee_id)
