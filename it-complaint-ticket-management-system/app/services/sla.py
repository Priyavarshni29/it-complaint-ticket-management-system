
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import AuthAccount, Notification, Ticket, SLAEscalation
from app.services.notifications import (
    notify_account,
    notify_team_leads,
)


SLA_TARGETS = {
    "Critical": {"response": 15, "resolution": 240},
    "High": {"response": 60, "resolution": 480},
    "Medium": {"response": 240, "resolution": 1440},
    "Low": {"response": 480, "resolution": 4320},
}

ACTIVE_STATUSES = ("Open", "In Progress")


def set_sla_deadlines(ticket: Ticket) -> None:
    """Set response and resolution deadlines using ticket priority."""
    start_time = ticket.created_at or datetime.now()
    targets = SLA_TARGETS.get(
        ticket.priority,
        SLA_TARGETS["Medium"],
    )

    ticket.response_due_at = start_time + timedelta(
        minutes=targets["response"]
    )
    ticket.resolution_due_at = start_time + timedelta(
        minutes=targets["resolution"]
    )


def notify_once(
    db,
    account_id: int,
    title: str,
    message: str,
    ticket_id: int,
) -> None:
    """Create a notification only if the same alert does not exist."""
    existing = (
        db.query(Notification)
        .filter(
            Notification.recipient_account_id == account_id,
            Notification.ticket_id == ticket_id,
            Notification.notification_type == "SLAEscalation",
            Notification.title == title,
        )
        .first()
    )

    if existing is None:
        notify_account(
            db,
            account_id,
            title,
            message,
            "SLAEscalation",
            ticket_id,
        )


def notify_assigned_staff(
    db,
    ticket: Ticket,
    breach_type: str,
) -> None:
    """Notify the staff member assigned to the breached ticket."""
    if not ticket.staff_id:
        return

    staff_account = (
        db.query(AuthAccount)
        .filter(
            AuthAccount.staff_id == ticket.staff_id,
            AuthAccount.role == "Staff",
        )
        .first()
    )

    if not staff_account:
        return

    title = f"{breach_type} SLA breached: #{ticket.ticket_id}"

    if breach_type == "Response":
        message = (
            f"The first-response deadline for ticket "
            f"#{ticket.ticket_id} ({ticket.title}) has passed."
        )
    else:
        message = (
            f"The resolution deadline for ticket "
            f"#{ticket.ticket_id} ({ticket.title}) has passed."
        )

    notify_once(
        db,
        staff_account.account_id,
        title,
        message,
        ticket.ticket_id,
    )


def notify_ticket_user(db, ticket: Ticket) -> None:
    """Notify the ticket owner about an overdue resolution."""
    if not ticket.user_id:
        return

    user_account = (
        db.query(AuthAccount)
        .filter(AuthAccount.user_id == ticket.user_id)
        .first()
    )

    if user_account:
        notify_once(
            db,
            user_account.account_id,
            f"Ticket resolution is overdue: #{ticket.ticket_id}",
            f"Ticket #{ticket.ticket_id} ({ticket.title}) "
            "has passed its resolution deadline.",
            ticket.ticket_id,
        )


def check_sla_breaches() -> None:
    """
    Check active tickets and create breach records and notifications.

    Resolved and closed tickets are excluded from automatic escalation.
    Existing breach flags are retained, and missing staff alerts are
    restored without repeatedly creating identical notifications.
    """
    now = datetime.now()

    with SessionLocal() as db:
        tickets = (
            db.query(Ticket)
            .filter(Ticket.status.in_(ACTIVE_STATUSES))
            .all()
        )

        for ticket in tickets:
            # Response SLA breach
            response_overdue = (
                ticket.response_due_at is not None
                and ticket.first_response_at is None
                and ticket.response_due_at <= now
            )

            if response_overdue:
                newly_breached = not ticket.response_sla_breached
                ticket.response_sla_breached = True

                if newly_breached:
                    db.add(
                        SLAEscalation(
                            ticket_id=ticket.ticket_id,
                            escalation_type="Response",
                            reason=(
                                "First response SLA deadline breached."
                            ),
                            escalated_from_staff_id=ticket.staff_id,
                        )
                    )

                    notify_team_leads(
                        db,
                        f"Response SLA breached: #{ticket.ticket_id}",
                        ticket.title,
                        "SLAEscalation",
                        ticket.ticket_id,
                    )

                # Also restores missing alerts for earlier breaches.
                notify_assigned_staff(db, ticket, "Response")

            # Resolution SLA breach
            resolution_overdue = (
                ticket.resolution_due_at is not None
                and ticket.resolution_due_at <= now
            )

            if resolution_overdue:
                newly_breached = not ticket.resolution_sla_breached
                ticket.resolution_sla_breached = True

                if newly_breached:
                    db.add(
                        SLAEscalation(
                            ticket_id=ticket.ticket_id,
                            escalation_type="Resolution",
                            reason=(
                                "Resolution SLA deadline breached."
                            ),
                            escalated_from_staff_id=ticket.staff_id,
                        )
                    )

                    notify_team_leads(
                        db,
                        f"Resolution SLA breached: #{ticket.ticket_id}",
                        ticket.title,
                        "SLAEscalation",
                        ticket.ticket_id,
                    )

                notify_assigned_staff(db, ticket, "Resolution")
                notify_ticket_user(db, ticket)

        db.commit()
