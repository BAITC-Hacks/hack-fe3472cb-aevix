from fastapi import APIRouter

from app.services.recommendation_service import get_employee_recommendations

router = APIRouter()


@router.get("/recommendations/{employee_id}")
def recommendations(employee_id: str) -> dict:
    return get_employee_recommendations(employee_id)
