
"""Add communication, SLA and notifications.

Revision ID: b4a890395d48
Revises: ef7df0928c76
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# Revision identifiers
revision: str = "b4a890395d48"
down_revision: Union[str, Sequence[str], None] = "ef7df0928c76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------
    # 1. Add SLA columns to existing tickets table
    # -----------------------------------------------------
    op.add_column(
        "tickets",
        sa.Column("response_due_at", mysql.DATETIME(fsp=0), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("resolution_due_at", mysql.DATETIME(fsp=0), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("first_response_at", mysql.DATETIME(fsp=0), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "response_sla_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "resolution_sla_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # -----------------------------------------------------
    # 2. Ticket messages and internal notes
    # -----------------------------------------------------
    op.create_table(
        "ticket_messages",
        sa.Column("message_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_account_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "visibility",
            sa.Enum("Public", "Internal"),
            nullable=False,
            server_default=sa.text("'Public'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "is_edited",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.ticket_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_account_id"],
            ["auth_accounts.account_id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_ticket_messages_message_id",
        "ticket_messages",
        ["message_id"],
    )
    op.create_index(
        "ix_ticket_messages_ticket_id",
        "ticket_messages",
        ["ticket_id"],
    )
    op.create_index(
        "ix_ticket_messages_sender_account_id",
        "ticket_messages",
        ["sender_account_id"],
    )
    op.create_index(
        "ix_ticket_messages_ticket_created",
        "ticket_messages",
        ["ticket_id", "created_at"],
    )

    # -----------------------------------------------------
    # 3. Staff-wide general chat
    # -----------------------------------------------------
    op.create_table(
        "staff_messages",
        sa.Column("message_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("sender_account_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["sender_account_id"],
            ["auth_accounts.account_id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_staff_messages_message_id",
        "staff_messages",
        ["message_id"],
    )
    op.create_index(
        "ix_staff_messages_sender_account_id",
        "staff_messages",
        ["sender_account_id"],
    )
    op.create_index(
        "ix_staff_messages_created",
        "staff_messages",
        ["created_at"],
    )

    # -----------------------------------------------------
    # 4. Notifications
    # -----------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column(
            "notification_id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("recipient_account_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column(
            "notification_type",
            sa.Enum(
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
        ),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("read_at", mysql.DATETIME(fsp=0), nullable=True),
        sa.ForeignKeyConstraint(
            ["recipient_account_id"],
            ["auth_accounts.account_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.ticket_id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_notifications_notification_id",
        "notifications",
        ["notification_id"],
    )
    op.create_index(
        "ix_notifications_recipient_account_id",
        "notifications",
        ["recipient_account_id"],
    )
    op.create_index(
        "ix_notifications_ticket_id",
        "notifications",
        ["ticket_id"],
    )
    op.create_index(
        "ix_notifications_recipient_read",
        "notifications",
        ["recipient_account_id", "is_read"],
    )

    # -----------------------------------------------------
    # 5. SLA escalation history
    # -----------------------------------------------------
    op.create_table(
        "sla_escalations",
        sa.Column(
            "escalation_id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column(
            "escalation_type",
            sa.Enum("Response", "Resolution", "Manual"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("escalated_from_staff_id", sa.Integer(), nullable=True),
        sa.Column("escalated_to_staff_id", sa.Integer(), nullable=True),
        sa.Column("escalated_by_account_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.ticket_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["escalated_from_staff_id"],
            ["staff.staff_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["escalated_to_staff_id"],
            ["staff.staff_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["escalated_by_account_id"],
            ["auth_accounts.account_id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_sla_escalations_escalation_id",
        "sla_escalations",
        ["escalation_id"],
    )
    op.create_index(
        "ix_sla_escalations_ticket_id",
        "sla_escalations",
        ["ticket_id"],
    )
    op.create_index(
        "ix_sla_escalations_ticket_created",
        "sla_escalations",
        ["ticket_id", "created_at"],
    )


def downgrade() -> None:
    # Remove only objects created by this migration.
    # Existing tickets, users, staff, categories and history remain.

    op.drop_table("sla_escalations")
    op.drop_table("notifications")
    op.drop_table("staff_messages")
    op.drop_table("ticket_messages")

    op.drop_column("tickets", "resolution_sla_breached")
    op.drop_column("tickets", "response_sla_breached")
    op.drop_column("tickets", "first_response_at")
    op.drop_column("tickets", "resolution_due_at")
    op.drop_column("tickets", "response_due_at")
