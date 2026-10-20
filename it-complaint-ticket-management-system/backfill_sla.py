
from app.database import SessionLocal
from app.models import Ticket
from app.services.sla import set_sla_deadlines


def backfill_sla_deadlines():
    with SessionLocal() as db:
        tickets = db.query(Ticket).all()
        updated = 0

        for ticket in tickets:
            if (
                ticket.response_due_at is None
                or ticket.resolution_due_at is None
            ):
                set_sla_deadlines(ticket)
                updated += 1
                print(
                    f"Ticket #{ticket.ticket_id}: "
                    f"response due={ticket.response_due_at}, "
                    f"resolution due={ticket.resolution_due_at}"
                )

        db.commit()
        print(f"\nCompleted. Updated {updated} ticket(s).")


if __name__ == "__main__":
    backfill_sla_deadlines()
