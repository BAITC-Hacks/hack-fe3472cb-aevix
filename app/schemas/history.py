from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ActivityHistoryBase(BaseModel):
    record_id: str
    employee_id: str
    event_id: str
    date: date | None = None
    due_date: date | None = None
    status: str | None = None
    completion_pct: int | None = None
    score: int | None = None
    feedback_rating: int | None = None
    assigned_by: str | None = None


class ActivityHistoryRead(ActivityHistoryBase):
    pass
