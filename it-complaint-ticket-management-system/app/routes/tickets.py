
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    Category,
    Ticket,
    TicketHistory,
    Staff,
    AuthAccount,
)
from app.schemas import TicketCreate, TicketResponse
from app.auth import get_current_account
from app.services.sla import set_sla_deadlines
from app.services.notifications import (
    notify_account,
    notify_team_leads,
)

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])

ACTIVE_STATUSES = ("Open", "In Progress")
ALLOWED_STATUSES = {"Open", "In Progress", "Resolved", "Closed"}


# ---------------- ACCESS CONTROL ----------------

def is_team_lead_or_admin(account: AuthAccount, db: Session) -> bool:
    if account.role == "Admin":
        return True

    if account.role == "Staff" and account.staff_id:
        staff = (
            db.query(Staff)
            .filter(Staff.staff_id == account.staff_id)
            .first()
        )
        return bool(staff and staff.is_team_lead)

    return False


def check_ticket_access(
    ticket: Ticket,
    account: AuthAccount,
    db: Session,
):
    if account.role == "Admin" or is_team_lead_or_admin(account, db):
        return

    if account.role == "User":
        if ticket.user_id != account.user_id:
            raise HTTPException(
                403, "You can access only your own tickets"
            )
        return

    if account.role == "Staff":
        if ticket.staff_id != account.staff_id:
            raise HTTPException(
                403, "You can access only tickets assigned to you"
            )
        return

    raise HTTPException(
        403, "You do not have permission to access this ticket"
    )


def require_staff(account: AuthAccount):
    if account.role != "Staff" or not account.staff_id:
        raise HTTPException(403, "Staff account required")


# ---------------- ASSIGNMENT HELPERS ----------------

def normalized_category(value: str) -> str:
    value = (value or "").strip().lower()

    aliases = {
        "hardware issue": "hardware",
        "hardware issues": "hardware",
        "network issue": "network",
        "network issues": "network",
        "software issue": "software",
        "software issues": "software",
        "security issue": "security",
        "security issues": "security",
    }
    return aliases.get(value, value)


def count_active_tickets(db: Session, staff_id: int) -> int:
    return (
        db.query(Ticket)
        .filter(
            Ticket.staff_id == staff_id,
            Ticket.status.in_(ACTIVE_STATUSES),
        )
        .count()
    )


def select_staff_for_ticket(
    db: Session,
    category_name: str,
) -> Staff | None:
    """Select available, matching staff by level, workload, and ID."""
    available_staff = (
        db.query(Staff)
        .filter(Staff.is_available.is_(True))
        .all()
    )

    category_key = normalized_category(category_name)

    matching_staff = [
        member
        for member in available_staff
        if normalized_category(member.specialization) == category_key
    ]

    if not matching_staff:
        return None

    level_rank = {"L1": 1, "L2": 2, "L3": 3}

    matching_staff.sort(
        key=lambda member: (
            level_rank.get(member.support_level, 99),
            count_active_tickets(db, member.staff_id),
            member.staff_id,
        )
    )

    return matching_staff[0]


def record_assignment(
    db: Session,
    ticket: Ticket,
    old_staff_id: int | None,
    new_staff_id: int | None,
):
    old_staff = (
        db.query(Staff)
        .filter(Staff.staff_id == old_staff_id)
        .first()
        if old_staff_id is not None
        else None
    )

    new_staff = (
        db.query(Staff)
        .filter(Staff.staff_id == new_staff_id)
        .first()
        if new_staff_id is not None
        else None
    )

    if old_staff_id == new_staff_id:
        return

    if new_staff:
        remarks = (
            f"Ticket assigned to {new_staff.name} "
            f"(staff ID {new_staff.staff_id})."
        )
    elif old_staff:
        remarks = (
            f"Ticket unassigned from {old_staff.name} "
            f"(staff ID {old_staff.staff_id})."
        )
    else:
        remarks = "Ticket remains in the unassigned queue."

    db.add(
        TicketHistory(
            ticket_id=ticket.ticket_id,
            old_status=ticket.status,
            new_status=ticket.status,
            remarks=remarks,
        )
    )


def notify_assignment(
    db: Session,
    ticket: Ticket,
    new_staff_id: int | None,
    old_staff_id: int | None = None,
):
    """Notify the employee, new assignee, or leads if unassigned."""
    user_account = (
        db.query(AuthAccount)
        .filter(AuthAccount.user_id == ticket.user_id)
        .first()
    )

    if new_staff_id is None:
        notify_team_leads(
            db,
            f"Unassigned ticket: #{ticket.ticket_id}",
            ticket.title,
            "TicketAssigned",
            ticket.ticket_id,
        )
    else:
        staff_account = (
            db.query(AuthAccount)
            .filter(AuthAccount.staff_id == new_staff_id)
            .first()
        )

        if staff_account:
            notify_account(
                db,
                staff_account.account_id,
                f"Ticket assigned: #{ticket.ticket_id}",
                ticket.title,
                "TicketAssigned",
                ticket.ticket_id,
            )

    if user_account:
        if old_staff_id is not None and old_staff_id != new_staff_id:
            title = f"Ticket #{ticket.ticket_id} reassigned"
            message = (
                "Your ticket has been reassigned to another staff member."
                if new_staff_id is not None
                else "Your ticket is currently awaiting staff assignment."
            )
            notification_type = "TicketReassigned"
        else:
            title = f"Ticket #{ticket.ticket_id} received"
            message = (
                "Your ticket has been assigned to support."
                if new_staff_id is not None
                else "Your ticket was received and is awaiting assignment."
            )
            notification_type = "TicketAssigned"

        notify_account(
            db,
            user_account.account_id,
            title,
            message,
            notification_type,
            ticket.ticket_id,
        )


# ---------------- CREATE TICKET ----------------

@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    if current_account.role != "User":
        raise HTTPException(
            403, "Only user accounts can submit complaints"
        )

    user_id = current_account.user_id
    if not user_id:
        raise HTTPException(
            403, "Account is not linked to a user record"
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, "User record not found")

    category = (
        db.query(Category)
        .filter(Category.category_id == ticket_data.category_id)
        .first()
    )
    if not category:
        raise HTTPException(404, "Category not found")

    matching_staff = select_staff_for_ticket(
        db, category.category_name
    )

    ticket = Ticket(
        user_id=user_id,
        staff_id=matching_staff.staff_id if matching_staff else None,
        category_id=ticket_data.category_id,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        status="Open",
    )

    try:
        db.add(ticket)
        db.flush()

        # Set response and resolution deadlines for the new ticket.
        set_sla_deadlines(ticket)

        if matching_staff:
            record_assignment(
                db, ticket, None, matching_staff.staff_id
            )

        notify_assignment(
            db,
            ticket,
            matching_staff.staff_id if matching_staff else None,
        )

        db.commit()
        db.refresh(ticket)
        return ticket

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        print(f"[NexaDesk] Ticket creation failed: {exc}")
        raise HTTPException(
            500,
            "Could not save the complaint, SLA deadlines, and notifications",
        )


# ---------------- GET TICKETS ----------------

@router.get("/", response_model=list[TicketResponse])
def get_tickets(
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    query = db.query(Ticket)

    if current_account.role == "User":
        query = query.filter(Ticket.user_id == current_account.user_id)

    elif current_account.role == "Staff":
        if not is_team_lead_or_admin(current_account, db):
            query = query.filter(
                Ticket.staff_id == current_account.staff_id
            )

    elif current_account.role != "Admin":
        raise HTTPException(
            403, "You do not have permission to view tickets"
        )

    return query.order_by(Ticket.created_at.desc()).all()


# ---------------- UNASSIGNED QUEUE ----------------

@router.get("/unassigned")
def get_unassigned_tickets(
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    require_staff(current_account)

    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.staff_id.is_(None),
            Ticket.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Ticket.created_at.asc())
        .all()
    )

    result = []
    for ticket in tickets:
        category = (
            db.query(Category)
            .filter(Category.category_id == ticket.category_id)
            .first()
        )

        result.append(
            {
                "ticket_id": ticket.ticket_id,
                "title": ticket.title,
                "description": ticket.description,
                "priority": ticket.priority,
                "status": ticket.status,
                "category_id": ticket.category_id,
                "category_name": (
                    category.category_name if category else None
                ),
                "created_at": ticket.created_at,
                "response_due_at": ticket.response_due_at,
                "resolution_due_at": ticket.resolution_due_at,
                "response_sla_breached": ticket.response_sla_breached,
                "resolution_sla_breached": ticket.resolution_sla_breached,
            }
        )

    return result


# ---------------- CLAIM UNASSIGNED TICKET ----------------

@router.post("/{ticket_id}/claim")
def claim_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    require_staff(current_account)

    staff = (
        db.query(Staff)
        .filter(Staff.staff_id == current_account.staff_id)
        .first()
    )
    if not staff:
        raise HTTPException(404, "Staff profile not found")

    if not staff.is_available:
        raise HTTPException(
            409,
            "You are unavailable. Mark yourself available before claiming.",
        )

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .with_for_update()
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if ticket.staff_id is not None:
        raise HTTPException(409, "This ticket has already been assigned")

    if ticket.status not in ACTIVE_STATUSES:
        raise HTTPException(
            409, "Only open or in-progress tickets can be claimed"
        )

    category = (
        db.query(Category)
        .filter(Category.category_id == ticket.category_id)
        .first()
    )

    if (
        category
        and normalized_category(staff.specialization)
        != normalized_category(category.category_name)
        and not is_team_lead_or_admin(current_account, db)
    ):
        raise HTTPException(
            403,
            "Your specialization does not match this ticket category",
        )

    old_staff_id = ticket.staff_id

    try:
        ticket.staff_id = staff.staff_id

        record_assignment(
            db, ticket, old_staff_id, staff.staff_id
        )

        notify_assignment(
            db, ticket, staff.staff_id, old_staff_id
        )

        db.commit()
        db.refresh(ticket)

        return {
            "message": "Ticket claimed successfully",
            "ticket_id": ticket.ticket_id,
            "staff_id": staff.staff_id,
            "status": ticket.status,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        print(f"[NexaDesk] Ticket claim failed: {exc}")
        raise HTTPException(500, "Could not claim ticket")


# ---------------- GET USERS ----------------

@router.get("/users")
def get_users(
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    if not is_team_lead_or_admin(current_account, db):
        raise HTTPException(
            403, "Only Team Leads or Admins can view all users"
        )

    users = db.query(User).order_by(User.name).all()

    return [
        {
            "user_id": user.user_id,
            "name": user.name,
            "department": user.department,
        }
        for user in users
    ]


# ---------------- GET CATEGORIES ----------------

@router.get("/categories")
def get_categories(
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    if current_account.role not in ("User", "Staff", "Admin"):
        raise HTTPException(
            403, "You do not have permission to view categories"
        )

    categories = (
        db.query(Category)
        .order_by(Category.category_name)
        .all()
    )

    return [
        {
            "category_id": category.category_id,
            "category_name": category.category_name,
        }
        for category in categories
    ]


# ---------------- GET TICKET HISTORY ----------------

@router.get("/{ticket_id}/history")
def get_ticket_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    check_ticket_access(ticket, current_account, db)

    history = (
        db.query(TicketHistory)
        .filter(TicketHistory.ticket_id == ticket_id)
        .order_by(
            TicketHistory.changed_at.asc(),
            TicketHistory.history_id.asc(),
        )
        .all()
    )

    return [
        {
            "history_id": record.history_id,
            "ticket_id": record.ticket_id,
            "old_status": record.old_status,
            "new_status": record.new_status,
            "changed_at": record.changed_at,
            "remarks": record.remarks,
        }
        for record in history
    ]


# ---------------- UPDATE TICKET STATUS ----------------

@router.patch("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    if current_account.role not in ("Staff", "Admin"):
        raise HTTPException(
            403, "Only Staff or Admin can update ticket status"
        )

    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(400, "Invalid status")

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .with_for_update()
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if (
        current_account.role == "Staff"
        and not is_team_lead_or_admin(current_account, db)
        and ticket.staff_id != current_account.staff_id
    ):
        raise HTTPException(
            403, "You can update only tickets assigned to you"
        )

    old_status = ticket.status
    if old_status == new_status:
        return {
            "message": "Ticket already has this status",
            "ticket_id": ticket_id,
            "status": new_status,
        }

    try:
        db.add(
            TicketHistory(
                ticket_id=ticket_id,
                old_status=old_status,
                new_status=new_status,
                remarks="Status updated through NexaDesk",
            )
        )

        ticket.status = new_status

        if new_status == "Resolved":
            ticket.resolved_at = datetime.now()
        elif old_status == "Resolved" and new_status != "Resolved":
            ticket.resolved_at = None

        user_account = (
            db.query(AuthAccount)
            .filter(AuthAccount.user_id == ticket.user_id)
            .first()
        )

        if user_account:
            notify_account(
                db,
                user_account.account_id,
                f"Ticket #{ticket.ticket_id} status updated",
                f"Status changed from {old_status} to {new_status}.",
                "StatusChanged",
                ticket.ticket_id,
            )

        # Inform the assigned staff member when a lead/admin updates
        # the ticket, without notifying the same account twice.
        if ticket.staff_id:
            assigned_account = (
                db.query(AuthAccount)
                .filter(AuthAccount.staff_id == ticket.staff_id)
                .first()
            )

            if (
                assigned_account
                and assigned_account.account_id != current_account.account_id
            ):
                notify_account(
                    db,
                    assigned_account.account_id,
                    f"Ticket #{ticket.ticket_id} status updated",
                    f"Status changed from {old_status} to {new_status}.",
                    "StatusChanged",
                    ticket.ticket_id,
                )

        db.commit()
        db.refresh(ticket)

        return {
            "message": "Ticket status updated successfully",
            "ticket_id": ticket.ticket_id,
            "old_status": old_status,
            "new_status": ticket.status,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        print(f"[NexaDesk] Status update failed: {exc}")
        raise HTTPException(
            500, "Could not update ticket status and history"
        )


# ---------------- GET ONE TICKET ----------------

@router.get("/{ticket_id}")
def get_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    check_ticket_access(ticket, current_account, db)

    user = (
        db.query(User)
        .filter(User.user_id == ticket.user_id)
        .first()
    )

    category = (
        db.query(Category)
        .filter(Category.category_id == ticket.category_id)
        .first()
    )

    assigned_staff = (
        db.query(Staff)
        .filter(Staff.staff_id == ticket.staff_id)
        .first()
        if ticket.staff_id is not None
        else None
    )

    return {
        "ticket_id": ticket.ticket_id,
        "title": ticket.title,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
        "staff_id": ticket.staff_id,
        "staff_name": assigned_staff.name if assigned_staff else None,
        "created_at": ticket.created_at,
        "resolved_at": ticket.resolved_at,
        "response_due_at": ticket.response_due_at,
        "resolution_due_at": ticket.resolution_due_at,
        "first_response_at": ticket.first_response_at,
        "response_sla_breached": ticket.response_sla_breached,
        "resolution_sla_breached": ticket.resolution_sla_breached,
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "department": user.department,
        } if user else None,
        "category": {
            "category_id": category.category_id,
            "category_name": category.category_name,
        } if category else None,
        "category_name": category.category_name if category else None,
    }
