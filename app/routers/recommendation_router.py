from typing import Literal

from fastapi import APIRouter

from app.services.recommendation_service import get_employee_recommendations

router = APIRouter()


@router.get("/recommendations/{employee_id}")
def recommendations(employee_id: str, include_explanations: bool = True, language: Literal["ru", "kk", "en"] = "en") -> dict:
    return get_employee_recommendations(employee_id, use_llm=include_explanations, language=language)
