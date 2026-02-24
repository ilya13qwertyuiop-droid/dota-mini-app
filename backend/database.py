"""
database.py — Central database configuration for the Dota Mini App.

Переключение между базами: задай DATABASE_URL в окружении.
  SQLite (default):   sqlite:///./backend/dota_bot.db
  PostgreSQL:         postgresql+psycopg2://user:pass@host:5432/dbname

Все остальные модули импортируют engine / Base / SessionLocal / get_db отсюда.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Connection URL
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./backend/dota_bot.db",
)

_is_sqlite: bool = DATABASE_URL.startswith("sqlite")

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_connect_args: dict = {}
if _is_sqlite:
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

# SQLite-specific: WAL mode + relaxed fsync for better read/write concurrency.
# These PRAGMAs are global (file-level), so setting them once at connect is enough.
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record) -> None:
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA synchronous=NORMAL")

# ---------------------------------------------------------------------------
# Session + Base
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency: yields a SQLAlchemy Session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Convenience: create all registered tables (idempotent, IF NOT EXISTS)
# ---------------------------------------------------------------------------

def create_all_tables() -> None:
    """Creates all tables defined in models.py (idempotent, IF NOT EXISTS).

    Imports all model modules here so they register with Base before create_all.
    For PostgreSQL in production, prefer Alembic migrations instead.
    """
    # Local imports: keeps database.py free of circular dependencies at module level
    from backend.models import (  # noqa: F401  (imported for Base registration)
        HeroMatchup,
        HeroMatchupsCache,
        HeroStat,
        HeroSynergy,
        Match,
        QuizResult,
        Token,
        UserProfile,
    )
    Base.metadata.create_all(bind=engine)
