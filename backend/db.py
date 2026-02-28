"""
db.py — Auth tokens and hero-matchups cache.

Previously used raw sqlite3.connect(). Now uses SQLAlchemy ORM via the
shared engine/SessionLocal from database.py so it works with both SQLite
and PostgreSQL without any code changes.

Public API is unchanged — callers (bot.py, api.py, hero_matchups_service.py)
don't need to be modified.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Support both invocation styles:
#   - as a module from project root: `python -m backend.db`
#   - as a script from backend/: used by bot.py which does `from db import ...`
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.database import SessionLocal  # noqa: E402
from backend.models import Feedback, HeroMatchupsCache, QuizResult, Token  # noqa: E402


# ---------------------------------------------------------------------------
# Schema init (idempotent; kept for backward compat with api.py + bot.py)
# ---------------------------------------------------------------------------

def init_tokens_table() -> None:
    """Ensures all tables exist. No-op if Alembic has already run."""
    from backend.database import create_all_tables
    create_all_tables()  # imports all models internally


def init_hero_matchups_cache_table() -> None:
    """Ensures all tables exist. No-op if Alembic has already run."""
    init_tokens_table()


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def create_token_for_user(user_id: int) -> str:
    """Generates a 24-hour token for the given Telegram user_id."""
    import secrets
    token_str = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    with SessionLocal() as session:
        # session.merge() = upsert by PK: inserts or replaces the row.
        # Replaces the former `INSERT OR REPLACE INTO tokens ...` (SQLite-only).
        token_obj = Token(token=token_str, user_id=user_id, expires_at=expires_at)
        session.merge(token_obj)
        session.commit()

    return token_str


def get_user_id_by_token(token: str) -> int | None:
    """Validates token and returns user_id, or None if missing/expired."""
    with SessionLocal() as session:
        token_obj = session.get(Token, token)

        if token_obj is None:
            return None

        if token_obj.expires_at < datetime.utcnow():
            session.delete(token_obj)
            session.commit()
            return None

        return token_obj.user_id


def delete_token(token: str) -> None:
    """Deletes a token (called when it's found to be expired)."""
    with SessionLocal() as session:
        token_obj = session.get(Token, token)
        if token_obj:
            session.delete(token_obj)
            session.commit()


# ---------------------------------------------------------------------------
# Hero matchups cache
# ---------------------------------------------------------------------------

def get_hero_matchups_from_cache(hero_id: int) -> tuple[list[dict], str | None]:
    """Reads cached matchup rows for a hero.

    Returns:
        - list of dicts {opponent_hero_id, games, wins, winrate, updated_at}
        - max updated_at for this hero_id (or None if no rows)
    """
    with SessionLocal() as session:
        rows = (
            session.query(HeroMatchupsCache)
            .filter(HeroMatchupsCache.hero_id == hero_id)
            .all()
        )

    if not rows:
        return [], None

    last_updated = max(r.updated_at for r in rows)
    matchups = [
        {
            "opponent_hero_id": r.opponent_hero_id,
            "games": r.games,
            "wins": r.wins,
            "winrate": r.winrate,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]
    return matchups, last_updated


# ---------------------------------------------------------------------------
# Quiz results
# ---------------------------------------------------------------------------

def get_last_quiz_result(user_id: int) -> tuple[dict, datetime] | None:
    """Returns (result_dict, updated_at) for the user's most recent quiz, or None.

    result_dict is already a Python dict (SQLAlchemy deserialises JSON columns).
    updated_at is a datetime (may be None if the row was saved without a timestamp).
    """
    with SessionLocal() as session:
        row = (
            session.query(QuizResult)
            .filter(QuizResult.user_id == user_id)
            .order_by(QuizResult.updated_at.desc())
            .first()
        )
    if row is None:
        return None
    return (row.result, row.updated_at)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def save_feedback(
    user_id: int | None,
    rating: int | None,
    tags: list[str],
    message: str,
    source: str,
    username: str | None = None,
) -> None:
    """Saves a feedback entry to the feedback table."""
    with SessionLocal() as session:
        fb = Feedback(
            user_id=user_id,
            username=username,
            rating=rating,
            tags=tags,
            message=message,
            source=source,
        )
        session.add(fb)
        session.commit()


def get_recent_feedback(limit: int = 20) -> list[dict]:
    """Returns the most recent feedback entries as plain dicts."""
    with SessionLocal() as session:
        rows = (
            session.query(Feedback)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": r.username,
                "rating": r.rating,
                "tags": r.tags or [],
                "message": r.message,
                "source": r.source,
                "created_at": r.created_at,
            }
            for r in rows
        ]


def replace_hero_matchups_in_cache(
    hero_id: int, matchups: list[dict], updated_at: str
) -> None:
    """Atomically replaces all cached matchup rows for a hero."""
    with SessionLocal() as session:
        session.query(HeroMatchupsCache).filter(
            HeroMatchupsCache.hero_id == hero_id
        ).delete(synchronize_session=False)

        for m in matchups:
            session.add(
                HeroMatchupsCache(
                    hero_id=hero_id,
                    opponent_hero_id=m["opponent_hero_id"],
                    games=m["games"],
                    wins=m["wins"],
                    winrate=m["winrate"],
                    updated_at=updated_at,
                )
            )
        session.commit()
