
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import test_database_connection
from app.routes.tickets import router as tickets_router

app = FastAPI(
    title="IT Complaint & Ticket Management System",
    description="API for submitting and tracking IT complaints",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.include_router(tickets_router)


@app.get("/health/db")
def database_health():
    return {
        "message": "Database connection successful",
        "database": test_database_connection(),
    }


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)
