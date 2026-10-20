
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification
from app.auth import get_current_account

router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


@router.get("/")
def list_notifications(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    return (
        db.query(Notification)
        .filter(
            Notification.recipient_account_id == account.account_id
        )
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    count = (
        db.query(Notification)
        .filter(
            Notification.recipient_account_id == account.account_id,
            Notification.is_read.is_(False),
        )
        .count()
    )
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.notification_id == notification_id,
            Notification.recipient_account_id == account.account_id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    notification.is_read = True
    notification.read_at = datetime.now()
    db.commit()

    return {"message": "Notification marked as read."}


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    (
        db.query(Notification)
        .filter(
            Notification.recipient_account_id == account.account_id,
            Notification.is_read.is_(False),
        )
        .update(
            {
                Notification.is_read: True,
                Notification.read_at: datetime.now(),
            },
            synchronize_session=False,
        )
    )

    db.commit()
    return {"message": "All notifications marked as read."}
