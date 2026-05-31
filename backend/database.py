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

_engine_kwargs: dict = {"connect_args": _connect_args}
if not _is_sqlite:
    # PostgreSQL: keep a warm connection pool; never let idle connections sit > 30 min.
    # pool_pre_ping validates each connection before use (detects stale TCP sockets).
    _engine_kwargs["pool_size"] = 10        # persistent connections
    _engine_kwargs["max_overflow"] = 20     # burst headroom (total max = 30)
    _engine_kwargs["pool_pre_ping"] = True  # re-connect on stale sockets
    _engine_kwargs["pool_recycle"] = 1800   # recycle connections every 30 min

engine = create_engine(DATABASE_URL, **_engine_kwargs)

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


# ---------------------------------------------------------------------------
# Startup-migration helpers (защита от дедлоков при одновременном старте)
# ---------------------------------------------------------------------------

# ID для pg_advisory_xact_lock — сериализует startup-миграции между процессами
# (несколько uvicorn-воркеров + bot стартуют одновременно). Значение
# произвольное, но обязано совпадать во всех вызовах. На SQLite не используется.
_STARTUP_MIGRATION_LOCK_ID = 9_876_543_210


def _column_exists(conn, table: str, column: str) -> bool:
    """Кросс-БД проверка наличия колонки. SQLite — PRAGMA, PG — information_schema.

    Используется ПЕРЕД ALTER TABLE в стартовых миграциях, чтобы на уже
    мигрированной БД ALTER не выполнялся вовсе. Иначе на PostgreSQL ALTER
    берёт AccessExclusiveLock на таблицу на время попытки даже при no-op
    исходе — и при параллельном старте нескольких процессов это даёт дедлок.
    """
    if _is_sqlite:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(r[1] == column for r in rows)
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


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
        AnalyticsEvent,
        BannedUser,
        HeroMatchup,
        HeroMatchupsCache,
        HeroStat,
        HeroSynergy,
        Match,
        MatchPlayer,
        QuizResult,
        Token,
        UserProfile,
    )
    Base.metadata.create_all(bind=engine)

    # Idempotent inline-миграция: user_profiles.created_at, если её нет.
    # Раньше это был голый try/except ALTER TABLE. На Postgres `ALTER TABLE`
    # ВСЕГДА берёт AccessExclusiveLock на таблицу на время попытки — даже
    # когда колонка уже есть и итог «no-op» (после try/except). При
    # одновременном старте нескольких процессов (uvicorn 4 воркера + bot)
    # параллельные попытки + живой трафик на user_profiles порождали дедлоки.
    #
    # Защита в два слоя:
    #   1) pg_advisory_xact_lock — сериализует startup-миграции между
    #      процессами в рамках одного движка; на SQLite не нужен (один писатель);
    #   2) existence-check через _column_exists — на уже мигрированной БД
    #      ALTER не выполняется вообще, всё превращается в один SELECT
    #      из information_schema без локов на пользовательской таблице.
    with engine.begin() as conn:
        if not _is_sqlite:
            conn.execute(
                text("SELECT pg_advisory_xact_lock(:id)"),
                {"id": _STARTUP_MIGRATION_LOCK_ID},
            )
        if not _column_exists(conn, "user_profiles", "created_at"):
            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN created_at TIMESTAMP"))
