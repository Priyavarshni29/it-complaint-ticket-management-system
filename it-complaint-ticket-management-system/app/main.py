
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import test_database_connection
from app.routes.tickets import router as tickets_router
from app.routes.auth_routes import router as auth_router
from app.routes.staff import router as staff_router
from app.routes.communications import router as communications_router
from app.routes.notifications import router as notifications_router
from app.routes.sla import router as sla_router
from app.services.sla import check_sla_breaches


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def sla_worker():
        while True:
            try:
                await asyncio.to_thread(check_sla_breaches)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[NexaDesk SLA] Checker error: {exc}")

            await asyncio.sleep(60)

    task = asyncio.create_task(sla_worker())

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="NexaDesk | IT Complaint & Ticket Management",
    description=(
        "Role-based IT complaint and ticket management portal "
        "with ticket conversations, notifications, SLA tracking, "
        "and escalation management."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(staff_router)
app.include_router(communications_router)
app.include_router(notifications_router)
app.include_router(sla_router)


@app.get("/health/db", tags=["Health"])
def database_health():
    return {
        "message": "Database connection successful",
        "database": test_database_connection(),
    }


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)
