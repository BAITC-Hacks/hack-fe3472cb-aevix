from fastapi import APIRouter, Depends, Query

from app.services.auth_service import require_employee_access
from app.services.recommendation_service import get_employee_recommendations

router = APIRouter(dependencies=[Depends(require_employee_access)])


@router.get("/recommendations/{employee_id}")
def recommendations(
    employee_id: str,
    include_explanations: bool = False,
    language: str = Query(default="ru", pattern="^(ru|kk|en)$"),
    limit: int = Query(default=3, ge=1, le=100),
) -> dict:
    return get_employee_recommendations(employee_id, limit=limit, use_llm=include_explanations, language=language)
