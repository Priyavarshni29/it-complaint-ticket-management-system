
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_account
from app.database import get_db
from app.models import AuthAccount, Staff, Ticket, SLAEscalation
from app.services.notifications import (
    notify_account,
    notify_team_leads,
)
from app.services.sla import SLA_TARGETS

router = APIRouter(prefix="/api/sla", tags=["SLA Management"])


def is_lead_or_admin(account, db: Session) -> bool:
    if account.role == "Admin":
        return True

    if account.role != "Staff" or not account.staff_id:
        return False

    staff = db.query(Staff).filter(
        Staff.staff_id == account.staff_id
    ).first()

    return bool(staff and staff.is_team_lead)


def require_lead_or_admin(account, db: Session):
    if not is_lead_or_admin(account, db):
        raise HTTPException(
            status_code=403,
            detail="Only Team Leads and Admins can access this feature.",
        )


@router.get("/targets")
def get_sla_targets(
    account=Depends(get_current_account),
):
    return SLA_TARGETS


@router.get("/tickets")
def get_ticket_sla_status(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    query = db.query(Ticket)

    if account.role == "User":
        query = query.filter(Ticket.user_id == account.user_id)

    elif account.role == "Staff":
        if is_lead_or_admin(account, db):
            pass
        else:
            query = query.filter(Ticket.staff_id == account.staff_id)

    elif account.role != "Admin":
        raise HTTPException(403, "Access denied")

    now = datetime.now()
    tickets = query.order_by(Ticket.created_at.desc()).all()

    result = []

    for ticket in tickets:
        response_remaining = (
            int((ticket.response_due_at - now).total_seconds())
            if ticket.response_due_at and not ticket.first_response_at
            else None
        )

        resolution_remaining = (
            int((ticket.resolution_due_at - now).total_seconds())
            if ticket.resolution_due_at
            and ticket.status not in ("Resolved", "Closed")
            else None
        )

        result.append({
            "ticket_id": ticket.ticket_id,
            "title": ticket.title,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_staff_id": ticket.staff_id,
            "response_due_at": ticket.response_due_at,
            "resolution_due_at": ticket.resolution_due_at,
            "first_response_at": ticket.first_response_at,
            "response_sla_breached": ticket.response_sla_breached,
            "resolution_sla_breached": ticket.resolution_sla_breached,
            "response_seconds_remaining": response_remaining,
            "resolution_seconds_remaining": resolution_remaining,
        })

    return result


@router.get("/report")
def get_sla_report(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    require_lead_or_admin(account, db)

    tickets = db.query(Ticket).all()
    total = len(tickets)

    response_breaches = sum(
        bool(t.response_sla_breached) for t in tickets
    )
    resolution_breaches = sum(
        bool(t.resolution_sla_breached) for t in tickets
    )

    response_applicable = sum(
        t.first_response_at is not None or t.response_sla_breached
        for t in tickets
    )
    resolution_applicable = sum(
        t.status in ("Resolved", "Closed")
        or t.resolution_sla_breached
        for t in tickets
    )

    escalations = (
        db.query(SLAEscalation)
        .order_by(SLAEscalation.created_at.desc())
        .all()
    )

    return {
        "total_tickets": total,
        "response_sla_breaches": response_breaches,
        "resolution_sla_breaches": resolution_breaches,
        "response_sla_compliance_percent": (
            round(
                100 * (response_applicable - response_breaches)
                / response_applicable,
                2,
            )
            if response_applicable else None
        ),
        "resolution_sla_compliance_percent": (
            round(
                100 * (resolution_applicable - resolution_breaches)
                / resolution_applicable,
                2,
            )
            if resolution_applicable else None
        ),
        "escalation_count": len(escalations),
    }


@router.get("/escalations")
def get_escalation_history(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    require_lead_or_admin(account, db)

    escalations = (
        db.query(SLAEscalation)
        .order_by(SLAEscalation.created_at.desc())
        .all()
    )

    return [
        {
            "escalation_id": e.escalation_id,
            "ticket_id": e.ticket_id,
            "escalation_type": e.escalation_type,
            "reason": e.reason,
            "escalated_from_staff_id": e.escalated_from_staff_id,
            "escalated_to_staff_id": e.escalated_to_staff_id,
            "escalated_by_account_id": e.escalated_by_account_id,
            "created_at": e.created_at,
        }
        for e in escalations
    ]


@router.post("/tickets/{ticket_id}/escalate")
def manually_escalate_ticket(
    ticket_id: int,
    reason: str = "Manual escalation by Team Lead",
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    require_lead_or_admin(account, db)

    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if ticket.status in ("Resolved", "Closed"):
        raise HTTPException(
            400,
            "Resolved or closed tickets cannot be escalated.",
        )

    # Route manual escalations to the first available team lead.
    lead = (
        db.query(Staff)
        .filter(
            Staff.is_team_lead.is_(True),
            Staff.is_available.is_(True),
        )
        .order_by(Staff.staff_id.asc())
        .first()
    )

    if lead is None:
        raise HTTPException(
            409,
            "No available Team Lead is configured for escalation.",
        )

    escalation = SLAEscalation(
        ticket_id=ticket.ticket_id,
        escalation_type="Manual",
        reason=reason[:500],
        escalated_from_staff_id=ticket.staff_id,
        escalated_to_staff_id=lead.staff_id,
        escalated_by_account_id=account.account_id,
    )

    db.add(escalation)

    lead_account = (
        db.query(AuthAccount)
        .filter(AuthAccount.staff_id == lead.staff_id)
        .first()
    )

    if lead_account:
        notify_account(
            db,
            lead_account.account_id,
            f"Manual escalation: ticket #{ticket.ticket_id}",
            ticket.title,
            "SLAEscalation",
            ticket.ticket_id,
        )

    if ticket.user_id:
        user_account = (
            db.query(AuthAccount)
            .filter(AuthAccount.user_id == ticket.user_id)
            .first()
        )

        if user_account:
            notify_account(
                db,
                user_account.account_id,
                f"Ticket #{ticket.ticket_id} escalated",
                "Your ticket has been escalated for additional attention.",
                "SLAEscalation",
                ticket.ticket_id,
            )

    db.commit()
    db.refresh(escalation)

    return {
        "message": "Ticket escalated successfully",
        "escalation_id": escalation.escalation_id,
        "ticket_id": ticket.ticket_id,
        "escalated_to_staff_id": lead.staff_id,
    }
