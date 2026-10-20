
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_account
from app.database import get_db
from app.models import (
    AuthAccount,
    Staff,
    Category,
    Ticket,
    TicketMessage,
    StaffMessage,
)
from app.services.notifications import (
    notify_account,
    notify_team_leads,
)

router = APIRouter(
    prefix="/api/communications",
    tags=["Communications"],
)


class TicketMessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    visibility: str = "Public"


class StaffMessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


def is_lead_or_admin(account, db: Session) -> bool:
    if account.role == "Admin":
        return True

    if account.role != "Staff" or not account.staff_id:
        return False

    staff = db.query(Staff).filter(
        Staff.staff_id == account.staff_id
    ).first()

    return bool(staff and staff.is_team_lead)


def can_access_ticket(ticket, account, db: Session) -> bool:
    if is_lead_or_admin(account, db):
        return True

    if account.role == "User":
        return ticket.user_id == account.user_id

    if account.role == "Staff":
        return ticket.staff_id == account.staff_id

    return False


def can_read_internal(ticket, account, db: Session) -> bool:
    if is_lead_or_admin(account, db):
        return True

    if account.role != "Staff" or not account.staff_id:
        return False

    staff = db.query(Staff).filter(
        Staff.staff_id == account.staff_id
    ).first()

    category = db.query(Category).filter(
        Category.category_id == ticket.category_id
    ).first()

    if not staff or not category:
        return False

    return (
        staff.specialization.strip().lower()
        == category.category_name.strip().lower()
    )


def get_accessible_ticket(ticket_id, account, db):
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if not can_access_ticket(ticket, account, db):
        raise HTTPException(
            403,
            "You do not have access to this ticket",
        )

    return ticket


@router.get("/tickets/{ticket_id}/messages")
def get_ticket_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    account: AuthAccount = Depends(get_current_account),
):
    ticket = get_accessible_ticket(ticket_id, account, db)

    query = db.query(TicketMessage).filter(
        TicketMessage.ticket_id == ticket_id
    )

    # Employees and regular staff must never receive internal notes
    # unless the staff member belongs to the ticket's support team.
    if not can_read_internal(ticket, account, db):
        query = query.filter(
            TicketMessage.visibility == "Public"
        )

    messages = query.order_by(
        TicketMessage.created_at.asc(),
        TicketMessage.message_id.asc(),
    ).all()

    return [
        {
            "message_id": m.message_id,
            "ticket_id": m.ticket_id,
            "sender_account_id": m.sender_account_id,
            "sender_email": m.sender.email if m.sender else None,
            "message": m.message,
            "visibility": m.visibility,
            "created_at": m.created_at,
            "is_edited": m.is_edited,
        }
        for m in messages
    ]


@router.post("/tickets/{ticket_id}/messages")
def send_ticket_message(
    ticket_id: int,
    payload: TicketMessageInput,
    db: Session = Depends(get_db),
    account: AuthAccount = Depends(get_current_account),
):
    ticket = get_accessible_ticket(ticket_id, account, db)

    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(400, "Message cannot be empty")

    visibility = payload.visibility

    if visibility not in ("Public", "Internal"):
        raise HTTPException(
            400,
            "Visibility must be Public or Internal",
        )

    # Employees can only send public messages.
    if visibility == "Internal":
        if not can_read_internal(ticket, account, db):
            raise HTTPException(
                403,
                "Only the ticket's support team, Team Leads, or Admins can add internal notes",
            )

    # Regular staff may only post to their assigned tickets.
    # Team Leads/Admins can access tickets for management.
    if account.role == "Staff" and not is_lead_or_admin(account, db):
        if ticket.staff_id != account.staff_id:
            raise HTTPException(
                403,
                "You can message only tickets assigned to you",
            )

    if account.role == "User" and visibility != "Public":
        raise HTTPException(403, "Employees can send public messages only")

    message = TicketMessage(
        ticket_id=ticket.ticket_id,
        sender_account_id=account.account_id,
        message=message_text,
        visibility=visibility,
        created_at=datetime.now(),
    )
    db.add(message)

    # The first public staff reply satisfies response SLA.
    if (
        visibility == "Public"
        and account.role in ("Staff", "Admin")
        and ticket.first_response_at is None
    ):
        ticket.first_response_at = datetime.now()

    # Notify the employee about public replies; internal notes
    # remain invisible to the employee.
    if visibility == "Public":
        user_account = (
            db.query(AuthAccount)
            .filter(AuthAccount.user_id == ticket.user_id)
            .first()
        )

        if user_account and user_account.account_id != account.account_id:
            notify_account(
                db,
                user_account.account_id,
                f"New message on ticket #{ticket.ticket_id}",
                f"A new reply was added to: {ticket.title}",
                "NewMessage",
                ticket.ticket_id,
            )

        if ticket.staff_id:
            assigned_account = (
                db.query(AuthAccount)
                .filter(AuthAccount.staff_id == ticket.staff_id)
                .first()
            )

            if (
                assigned_account
                and assigned_account.account_id != account.account_id
            ):
                notify_account(
                    db,
                    assigned_account.account_id,
                    f"New message on ticket #{ticket.ticket_id}",
                    f"A reply was added to: {ticket.title}",
                    "NewMessage",
                    ticket.ticket_id,
                )
    else:
        notify_team_leads(
            db,
            f"Internal note on ticket #{ticket.ticket_id}",
            f"An internal note was added to: {ticket.title}",
            "InternalNote",
            ticket.ticket_id,
        )

    db.commit()
    db.refresh(message)

    return {
        "message_id": message.message_id,
        "ticket_id": message.ticket_id,
        "message": message.message,
        "visibility": message.visibility,
        "created_at": message.created_at,
    }


@router.get("/staff-chat")
def get_staff_chat(
    db: Session = Depends(get_db),
    account: AuthAccount = Depends(get_current_account),
):
    if account.role not in ("Staff", "Admin"):
        raise HTTPException(
            403,
            "Staff chat is available to Staff and Admin accounts only",
        )

    messages = (
        db.query(StaffMessage)
        .order_by(
            StaffMessage.created_at.asc(),
            StaffMessage.message_id.asc(),
        )
        .limit(200)
        .all()
    )

    return [
        {
            "message_id": m.message_id,
            "sender_account_id": m.sender_account_id,
            "sender_email": m.sender.email if m.sender else None,
            "message": m.message,
            "created_at": m.created_at,
        }
        for m in messages
    ]


@router.post("/staff-chat")
def send_staff_chat(
    payload: StaffMessageInput,
    db: Session = Depends(get_db),
    account: AuthAccount = Depends(get_current_account),
):
    if account.role not in ("Staff", "Admin"):
        raise HTTPException(
            403,
            "Staff chat is available to Staff and Admin accounts only",
        )

    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(400, "Message cannot be empty")

    message = StaffMessage(
        sender_account_id=account.account_id,
        message=message_text,
        created_at=datetime.now(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "message_id": message.message_id,
        "message": message.message,
        "created_at": message.created_at,
    }
