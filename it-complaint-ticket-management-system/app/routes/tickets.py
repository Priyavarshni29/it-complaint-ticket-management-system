
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Category, Ticket, TicketHistory
from app.schemas import TicketCreate, TicketResponse

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


# --------------------------------------------------
# CREATE A NEW TICKET
# --------------------------------------------------
@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.user_id == ticket_data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    category = db.query(Category).filter(
        Category.category_id == ticket_data.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    ticket = Ticket(
        user_id=ticket_data.user_id,
        category_id=ticket_data.category_id,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        status="Open",
    )

    try:
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the complaint",
        )


# --------------------------------------------------
# GET ALL TICKETS
# --------------------------------------------------
@router.get("/", response_model=list[TicketResponse])
def get_tickets(db: Session = Depends(get_db)):
    return (
        db.query(Ticket)
        .order_by(Ticket.created_at.desc())
        .all()
    )


# --------------------------------------------------
# GET ALL USERS
# IMPORTANT: Keep this before /{ticket_id}
# --------------------------------------------------
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .order_by(User.name)
        .all()
    )

    return [
        {
            "user_id": user.user_id,
            "name": user.name,
            "department": user.department,
        }
        for user in users
    ]


# --------------------------------------------------
# GET ALL CATEGORIES
# IMPORTANT: Keep this before /{ticket_id}
# --------------------------------------------------
@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
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


# --------------------------------------------------
# GET STATUS HISTORY FOR A TICKET
# --------------------------------------------------
@router.get("/{ticket_id}/history")
def get_ticket_history(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

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


# --------------------------------------------------
# UPDATE TICKET STATUS
# --------------------------------------------------
@router.patch("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    new_status: str,
    db: Session = Depends(get_db),
):
    allowed_statuses = {
        "Open",
        "In Progress",
        "Resolved",
        "Closed",
    }

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status",
        )

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .with_for_update()
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    old_status = ticket.status

    if old_status == new_status:
        return {
            "message": "Ticket already has this status",
            "ticket_id": ticket_id,
            "status": new_status,
        }

    try:
        history = TicketHistory(
            ticket_id=ticket_id,
            old_status=old_status,
            new_status=new_status,
            remarks="Status updated through the IT Support Portal",
        )

        ticket.status = new_status

        if new_status == "Resolved":
            ticket.resolved_at = datetime.now()

        elif (
            old_status == "Resolved"
            and new_status != "Resolved"
        ):
            ticket.resolved_at = None

        db.add(history)
        db.commit()
        db.refresh(ticket)

        return {
            "message": "Ticket status updated successfully",
            "ticket_id": ticket.ticket_id,
            "old_status": old_status,
            "new_status": ticket.status,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update ticket status and history",
        )


# --------------------------------------------------
# GET DETAILS OF ONE TICKET
# Keep the general /{ticket_id} route last.
# --------------------------------------------------
@router.get("/{ticket_id}")
def get_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    user = db.query(User).filter(
        User.user_id == ticket.user_id
    ).first()

    category = db.query(Category).filter(
        Category.category_id == ticket.category_id
    ).first()

    return {
        "ticket_id": ticket.ticket_id,
        "title": ticket.title,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "resolved_at": ticket.resolved_at,
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "department": user.department,
        } if user else None,
        "category": {
            "category_id": category.category_id,
            "category_name": category.category_name,
        } if category else None,
    }
