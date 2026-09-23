from fastapi import APIRouter

from app.schemas.hr import HRDashboard
from app.services.hr_service import get_hr_dashboard
from app.services.esg_service import engagement

router = APIRouter()


@router.get("/dashboard", response_model=HRDashboard)
def hr_dashboard() -> dict:
    return get_hr_dashboard()


@router.get("/skill-gaps", response_model=HRDashboard)
def skill_gaps() -> dict:
    return get_hr_dashboard()


@router.get("/inactive-employees", response_model=HRDashboard)
def inactive_employees() -> dict:
    return get_hr_dashboard()


@router.get("/events-effectiveness", response_model=HRDashboard)
def events_effectiveness() -> dict:
    return get_hr_dashboard()


@router.get("/esg-engagement")
def esg_engagement() -> dict:
    return engagement()
