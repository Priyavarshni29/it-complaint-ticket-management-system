
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# COMMON TYPES
# =========================================================

Priority = Literal["Low", "Medium", "High", "Critical"]

TicketStatus = Literal[
    "Open",
    "In Progress",
    "Resolved",
    "Closed",
]

MessageVisibility = Literal["Public", "Internal"]

NotificationType = Literal[
    "StatusChanged",
    "TicketAssigned",
    "TicketReassigned",
    "NewMessage",
    "InternalNote",
    "SLAWarning",
    "SLAEscalation",
    "General",
]

EscalationType = Literal["Response", "Resolution", "Manual"]


# =========================================================
# TICKET SCHEMAS
# =========================================================

class TicketCreate(BaseModel):
    category_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5)
    priority: Priority = "Medium"


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: int
    user_id: int | None = None
    staff_id: int | None
    category_id: int
    title: str
    description: str
    priority: Priority
    status: TicketStatus
    created_at: datetime
    resolved_at: datetime | None

    response_due_at: datetime | None = None
    resolution_due_at: datetime | None = None
    first_response_at: datetime | None = None
    response_sla_breached: bool = False
    resolution_sla_breached: bool = False


# =========================================================
# TICKET CONVERSATION AND INTERNAL NOTES
# =========================================================

class TicketMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    visibility: MessageVisibility = "Public"


class TicketMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    ticket_id: int
    sender_account_id: int
    message: str
    visibility: MessageVisibility
    created_at: datetime
    is_edited: bool


# =========================================================
# STAFF-WIDE CHAT
# =========================================================

class StaffMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class StaffMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    sender_account_id: int
    message: str
    created_at: datetime


# =========================================================
# NOTIFICATIONS
# =========================================================

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    recipient_account_id: int
    ticket_id: int | None
    notification_type: NotificationType
    title: str
    message: str
    created_at: datetime
    is_read: bool
    read_at: datetime | None


class NotificationReadResponse(BaseModel):
    notification_id: int
    is_read: bool
    read_at: datetime | None


class UnreadNotificationCount(BaseModel):
    unread_count: int = Field(ge=0)


# =========================================================
# SLA AND ESCALATION
# =========================================================

class SLAStatusResponse(BaseModel):
    ticket_id: int
    priority: Priority
    status: TicketStatus

    created_at: datetime
    first_response_at: datetime | None = None
    response_due_at: datetime | None = None
    resolution_due_at: datetime | None = None

    response_sla_breached: bool
    resolution_sla_breached: bool

    # Seconds remaining until each deadline.
    # Negative values indicate an overdue deadline.
    response_seconds_remaining: int | None = None
    resolution_seconds_remaining: int | None = None


class SLAEscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    escalation_id: int
    ticket_id: int
    escalation_type: EscalationType
    reason: str
    escalated_from_staff_id: int | None
    escalated_to_staff_id: int | None
    escalated_by_account_id: int | None
    created_at: datetime


class ManualEscalationCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    escalated_to_staff_id: int | None = Field(default=None, gt=0)


# =========================================================
# SLA REPORTING
# =========================================================

class SLAReportResponse(BaseModel):
    total_tickets: int = Field(ge=0)
    response_sla_breached: int = Field(ge=0)
    resolution_sla_breached: int = Field(ge=0)
    response_sla_compliance_percent: float = Field(ge=0, le=100)
    resolution_sla_compliance_percent: float = Field(ge=0, le=100)
