
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    DateTime,
    ForeignKey,
    Boolean,
    text,
    Index,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import relationship

from app.database import Base


# =========================================================
# USER
# =========================================================

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    contact_no = Column(String(20), nullable=True)


# =========================================================
# STAFF
# =========================================================

class Staff(Base):
    __tablename__ = "staff"

    staff_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    specialization = Column(String(100), nullable=False)
    contact_no = Column(String(20), nullable=True)

    support_level = Column(
        Enum("L1", "L2", "L3"),
        nullable=False,
        default="L1",
    )

    is_team_lead = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_available = Column(
        Boolean,
        nullable=False,
        default=True,
    )


# =========================================================
# CATEGORY
# =========================================================

class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(80), unique=True, nullable=False)
    description = Column(String(255), nullable=True)


# =========================================================
# TICKET
# =========================================================

class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
    )

    staff_id = Column(
        Integer,
        ForeignKey("staff.staff_id"),
        nullable=True,
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.category_id"),
        nullable=False,
    )

    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)

    priority = Column(
        Enum("Low", "Medium", "High", "Critical"),
        nullable=False,
        server_default=text("'Medium'"),
    )

    status = Column(
        Enum("Open", "In Progress", "Resolved", "Closed"),
        nullable=False,
        server_default=text("'Open'"),
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    resolved_at = Column(DATETIME(fsp=0), nullable=True)

    # SLA tracking
    response_due_at = Column(DATETIME(fsp=0), nullable=True)
    resolution_due_at = Column(DATETIME(fsp=0), nullable=True)
    first_response_at = Column(DATETIME(fsp=0), nullable=True)

    # These flags help the background checker avoid
    # repeatedly escalating the same SLA breach.
    response_sla_breached = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    resolution_sla_breached = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    # ORM relationships
    user = relationship("User", foreign_keys=[user_id])
    staff = relationship("Staff", foreign_keys=[staff_id])
    category = relationship("Category", foreign_keys=[category_id])

    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    history_entries = relationship(
        "TicketHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    escalations = relationship(
        "SLAEscalation",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )


# =========================================================
# TICKET HISTORY
# =========================================================

class TicketHistory(Base):
    __tablename__ = "ticket_history"

    history_id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.ticket_id"),
        nullable=False,
    )

    old_status = Column(
        Enum("Open", "In Progress", "Resolved", "Closed"),
        nullable=True,
    )

    new_status = Column(
        Enum("Open", "In Progress", "Resolved", "Closed"),
        nullable=False,
    )

    changed_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    remarks = Column(String(500), nullable=True)

    ticket = relationship("Ticket", back_populates="history_entries")


# =========================================================
# AUTHENTICATION ACCOUNT
# =========================================================

class AuthAccount(Base):
    __tablename__ = "auth_accounts"

    account_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    role = Column(
        Enum("User", "Staff", "Admin"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )

    staff_id = Column(
        Integer,
        ForeignKey("staff.staff_id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )


# =========================================================
# TICKET CONVERSATION AND INTERNAL NOTES
# =========================================================

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    message_id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_account_id = Column(
        Integer,
        ForeignKey("auth_accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message = Column(Text, nullable=False)

    # Public: employee and authorized ticket staff can see it.
    # Internal: authorized staff and Team Leads/Admin only.
    visibility = Column(
        Enum("Public", "Internal"),
        nullable=False,
        server_default=text("'Public'"),
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    is_edited = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    ticket = relationship("Ticket", back_populates="messages")

    sender = relationship(
        "AuthAccount",
        foreign_keys=[sender_account_id],
    )

    __table_args__ = (
        Index("ix_ticket_messages_ticket_created", "ticket_id", "created_at"),
    )


# =========================================================
# STAFF-WIDE GENERAL CHAT
# =========================================================

class StaffMessage(Base):
    __tablename__ = "staff_messages"

    message_id = Column(Integer, primary_key=True, index=True)

    sender_account_id = Column(
        Integer,
        ForeignKey("auth_accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    sender = relationship(
        "AuthAccount",
        foreign_keys=[sender_account_id],
    )

    __table_args__ = (
        Index("ix_staff_messages_created", "created_at"),
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)

    recipient_account_id = Column(
        Integer,
        ForeignKey("auth_accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    notification_type = Column(
        Enum(
            "StatusChanged",
            "TicketAssigned",
            "TicketReassigned",
            "NewMessage",
            "InternalNote",
            "SLAWarning",
            "SLAEscalation",
            "General",
        ),
        nullable=False,
    )

    title = Column(String(150), nullable=False)
    message = Column(String(500), nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    read_at = Column(DATETIME(fsp=0), nullable=True)

    recipient = relationship(
        "AuthAccount",
        foreign_keys=[recipient_account_id],
    )

    ticket = relationship("Ticket", foreign_keys=[ticket_id])

    __table_args__ = (
        Index(
            "ix_notifications_recipient_read",
            "recipient_account_id",
            "is_read",
        ),
    )


# =========================================================
# SLA ESCALATION HISTORY
# =========================================================

class SLAEscalation(Base):
    __tablename__ = "sla_escalations"

    escalation_id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    escalation_type = Column(
        Enum("Response", "Resolution", "Manual"),
        nullable=False,
    )

    reason = Column(String(500), nullable=False)

    escalated_from_staff_id = Column(
        Integer,
        ForeignKey("staff.staff_id", ondelete="SET NULL"),
        nullable=True,
    )

    escalated_to_staff_id = Column(
        Integer,
        ForeignKey("staff.staff_id", ondelete="SET NULL"),
        nullable=True,
    )

    escalated_by_account_id = Column(
        Integer,
        ForeignKey("auth_accounts.account_id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    ticket = relationship("Ticket", back_populates="escalations")

    escalated_from_staff = relationship(
        "Staff",
        foreign_keys=[escalated_from_staff_id],
    )

    escalated_to_staff = relationship(
        "Staff",
        foreign_keys=[escalated_to_staff_id],
    )

    escalated_by = relationship(
        "AuthAccount",
        foreign_keys=[escalated_by_account_id],
    )

    __table_args__ = (
        Index("ix_sla_escalations_ticket_created", "ticket_id", "created_at"),
    )
