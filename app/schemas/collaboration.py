from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class TeamCreate(BaseModel):
    creator_id: Identifier
    name: DisplayName = "Career Quest Team"
    max_members: int = Field(default=5, ge=1, strict=True)


class TeamJoin(BaseModel):
    employee_id: Identifier


class PairInvitationCreate(BaseModel):
    inviter_id: Identifier
    event_id: Identifier
    format: Literal["online_together", "in_person", "self_paced_discussion"]
    start_date: date | None = None
    end_date: date | None = None
    display_mode: Literal["name", "alias"] = "name"
    display_name: DisplayName | None = None

    @model_validator(mode="after")
    def check_date_range(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class PairInvitationResponse(BaseModel):
    employee_id: Identifier
    decision: Literal["accept", "decline"] = "accept"
