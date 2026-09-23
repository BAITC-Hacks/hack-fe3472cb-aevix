from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel


class ActivityHistoryBase(BaseModel):
    record_id: str
    employee_id: str
    event_id: str
    date: Date | None = None
    due_date: Date | None = None
    status: str | None = None
    completion_pct: int | None = None
    score: int | None = None
    feedback_rating: int | None = None
    assigned_by: str | None = None


class ActivityHistoryRead(ActivityHistoryBase):
    pass
