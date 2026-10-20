
from sqlalchemy.orm import Session

from app.models import AuthAccount, Notification


def notify_account(
    db: Session,
    account_id: int,
    title: str,
    message: str,
    notification_type: str = "General",
    ticket_id: int | None = None,
) -> Notification:
    notification = Notification(
        recipient_account_id=account_id,
        ticket_id=ticket_id,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False,
    )
    db.add(notification)
    return notification


def notify_role(
    db: Session,
    role: str,
    title: str,
    message: str,
    notification_type: str = "General",
    ticket_id: int | None = None,
) -> None:
    accounts = (
        db.query(AuthAccount)
        .filter(AuthAccount.role == role)
        .all()
    )

    for account in accounts:
        notify_account(
            db=db,
            account_id=account.account_id,
            title=title,
            message=message,
            notification_type=notification_type,
            ticket_id=ticket_id,
        )


def notify_team_leads(
    db: Session,
    title: str,
    message: str,
    notification_type: str,
    ticket_id: int | None = None,
) -> None:
    from app.models import Staff

    accounts = (
        db.query(AuthAccount)
        .join(Staff, AuthAccount.staff_id == Staff.staff_id)
        .filter(
            AuthAccount.role == "Staff",
            Staff.is_team_lead.is_(True),
        )
        .all()
    )

    for account in accounts:
        notify_account(
            db,
            account.account_id,
            title,
            message,
            notification_type,
            ticket_id,
        )
