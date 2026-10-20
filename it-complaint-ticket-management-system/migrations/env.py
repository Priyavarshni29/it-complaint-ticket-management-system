
from logging.config import fileConfig
import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# Make the project root importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from the project .env file
load_dotenv(PROJECT_ROOT / ".env")

from app.database import Base
import app.models  # Register all SQLAlchemy models with Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which SQLAlchemy metadata to inspect
target_metadata = Base.metadata


def get_database_url():
    """Read the existing database connection from environment variables."""
    url = os.getenv("DATABASE_URL")

    if url:
        return url

    # Support projects that store individual DB settings instead.
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    database = os.getenv("DB_NAME", "it_complaint_system")

    if user is None or password is None:
        raise RuntimeError(
            "Database settings not found. Check the variable names "
            "used in app/database.py and your .env file."
        )

    from sqlalchemy.engine import URL

    return URL.create(
        "mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )


def run_migrations_offline():
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
