
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Staff, Ticket, AuthAccount
from app.auth import get_current_account

router = APIRouter(prefix="/api/staff", tags=["Staff Management"])


class AvailabilityUpdate(BaseModel):
    is_available: bool


def get_staff_for_account(
    account: AuthAccount,
    db: Session,
) -> Staff:
    """Return the staff record associated with the logged-in account."""
    if account.role != "Staff" or not account.staff_id:
        raise HTTPException(
            status_code=403,
            detail="Staff account required",
        )

    staff = (
        db.query(Staff)
        .filter(Staff.staff_id == account.staff_id)
        .first()
    )

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Staff profile not found",
        )

    return staff


def require_team_lead(account: AuthAccount, db: Session):
    """Allow Team Leads and Admins to manage the team directory."""
    if account.role == "Admin":
        return

    staff = get_staff_for_account(account, db)

    if not staff.is_team_lead:
        raise HTTPException(
            status_code=403,
            detail="Team Lead access required",
        )


def active_ticket_count(db: Session, staff_id: int) -> int:
    return (
        db.query(Ticket)
        .filter(
            Ticket.staff_id == staff_id,
            Ticket.status.notin_(["Resolved", "Closed"]),
        )
        .count()
    )


@router.get("/me")
def my_staff_profile(
    account: AuthAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Return the logged-in staff member's own availability and workload."""
    staff = get_staff_for_account(account, db)

    return {
        "staff_id": staff.staff_id,
        "name": staff.name,
        "email": staff.email,
        "specialization": staff.specialization,
        "support_level": staff.support_level,
        "is_available": staff.is_available,
        "is_team_lead": staff.is_team_lead,
        "active_tickets": active_ticket_count(db, staff.staff_id),
    }


@router.patch("/me/availability")
def update_my_availability(
    payload: AvailabilityUpdate,
    account: AuthAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Let a staff member change their own availability."""
    staff = get_staff_for_account(account, db)

    staff.is_available = payload.is_available
    db.commit()
    db.refresh(staff)

    return {
        "message": (
            "You are now available"
            if staff.is_available
            else "You are now unavailable"
        ),
        "staff_id": staff.staff_id,
        "is_available": staff.is_available,
    }


@router.get("/")
def list_staff(
    account: AuthAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Show the team directory to Team Leads and Admins."""
    require_team_lead(account, db)

    staff_members = db.query(Staff).order_by(Staff.name).all()

    return [
        {
            "staff_id": member.staff_id,
            "name": member.name,
            "email": member.email,
            "specialization": member.specialization,
            "support_level": member.support_level,
            "is_available": member.is_available,
            "is_team_lead": member.is_team_lead,
            "active_tickets": active_ticket_count(
                db, member.staff_id
            ),
        }
        for member in staff_members
    ]


@router.patch("/{staff_id}/availability")
def update_staff_availability(
    staff_id: int,
    payload: AvailabilityUpdate,
    account: AuthAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Let Team Leads/Admins manage another staff member's availability."""
    require_team_lead(account, db)

    member = (
        db.query(Staff)
        .filter(Staff.staff_id == staff_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Staff member not found",
        )

    member.is_available = payload.is_available
    db.commit()
    db.refresh(member)

    return {
        "message": "Staff availability updated",
        "staff_id": member.staff_id,
        "is_available": member.is_available,
    }
