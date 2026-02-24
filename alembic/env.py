"""
alembic/env.py — Alembic migration environment.

DATABASE_URL is read from the environment (same variable the app uses),
so running migrations always targets the same DB as the application.

Usage:
    # SQLite (default):
    alembic upgrade head

    # PostgreSQL:
    DATABASE_URL=postgresql+psycopg2://user:pass@host/dbname alembic upgrade head
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# Ensure project root is on sys.path so `from backend.*` imports work
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Alembic Config object (gives access to alembic.ini values)
# ---------------------------------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import app engine + all models (registers them with Base.metadata)
# ---------------------------------------------------------------------------

from backend.database import DATABASE_URL, engine  # noqa: E402
from backend.models import (  # noqa: F401, E402  (imported for Base registration)
    HeroMatchup,
    HeroMatchupsCache,
    HeroStat,
    HeroSynergy,
    Match,
    QuizResult,
    Token,
    UserProfile,
)
from backend.database import Base  # noqa: E402

# Override sqlalchemy.url with the runtime value from env
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required).

    Emits SQL to stdout / a file. Useful for generating migration scripts
    to review or apply manually.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the DB directly)."""
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
