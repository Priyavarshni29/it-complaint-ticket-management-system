
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Priority = Literal["Low", "Medium", "High", "Critical"]
TicketStatus = Literal["Open", "In Progress", "Resolved", "Closed"]


class TicketCreate(BaseModel):
    user_id: int = Field(gt=0)
    category_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5)
    priority: Priority = "Medium"


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: int
    user_id: int
    staff_id: int | None
    category_id: int
    title: str
    description: str
    priority: Priority
    status: TicketStatus
    created_at: datetime
    resolved_at: datetime | None
