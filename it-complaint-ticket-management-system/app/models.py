
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    contact_no = Column(String(20), nullable=True)


class Staff(Base):
    __tablename__ = "staff"

    staff_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    specialization = Column(String(100), nullable=False)
    contact_no = Column(String(20), nullable=True)


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(80), unique=True, nullable=False)
    description = Column(String(255), nullable=True)


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.staff_id"), nullable=True)
    category_id = Column(
        Integer, ForeignKey("categories.category_id"), nullable=False
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
