from fastapi import APIRouter

from app.services.hr_service import get_hr_dashboard

router = APIRouter()


@router.get("/dashboard")
def hr_dashboard() -> dict:
    return get_hr_dashboard()


@router.get("/skill-gaps")
def skill_gaps() -> dict:
    return get_hr_dashboard()


@router.get("/inactive-employees")
def inactive_employees() -> dict:
    return get_hr_dashboard()


@router.get("/events-effectiveness")
def events_effectiveness() -> dict:
    return get_hr_dashboard()
