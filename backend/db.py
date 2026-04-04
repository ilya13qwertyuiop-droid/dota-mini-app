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
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Support both invocation styles:
#   - as a module from project root: `python -m backend.db`
#   - as a script from backend/: used by bot.py which does `from db import ...`
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.database import SessionLocal  # noqa: E402
from backend.models import DotaNews, DraftResult, Feedback, HeroMatchupsCache, Match, QuizResult, Token, UserProfile  # noqa: E402


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


def get_feedback_stats() -> dict:
    """Returns total feedback count and average rating."""
    from sqlalchemy import func
    with SessionLocal() as session:
        total = session.query(func.count(Feedback.id)).scalar() or 0
        avg = session.query(func.avg(Feedback.rating)).scalar()
        return {"total": total, "avg_rating": round(avg, 2) if avg is not None else None}


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


def upsert_user_profile_settings(user_id: int, settings_patch: dict) -> None:
    """Creates or updates user_profiles.settings fields (shallow merge).

    Used by bot.py /start to persist Telegram profile data without making a
    self-HTTP call to the API server. Equivalent to POST /api/save_telegram_data,
    but runs in-process with a direct DB write.
    """
    from sqlalchemy.orm.attributes import flag_modified

    with SessionLocal() as session:
        profile = session.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                favorite_heroes=[],
                settings=settings_patch,
            )
            session.add(profile)
        else:
            current = dict(profile.settings or {})
            current.update(settings_patch)
            profile.settings = current
            flag_modified(profile, "settings")
        session.commit()


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


# ---------------------------------------------------------------------------
# Admin statistics
# ---------------------------------------------------------------------------

def count_new_users_today() -> int:
    """Counts user_profiles created today (UTC). Rows with NULL created_at are excluded."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    # Strip timezone for comparison — SQLite stores datetimes as naive strings
    today_start_naive = today_start.replace(tzinfo=None)
    with SessionLocal() as session:
        return (
            session.query(UserProfile)
            .filter(UserProfile.created_at >= today_start_naive)
            .count()
        )


def count_active_users_30d() -> int:
    """Counts distinct user_ids with any quiz_result updated in the last 30 days."""
    from sqlalchemy import func
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    with SessionLocal() as session:
        return (
            session.query(func.count(func.distinct(QuizResult.user_id)))
            .filter(QuizResult.updated_at >= thirty_days_ago)
            .scalar()
            or 0
        )


def count_matches_with_game_mode() -> int:
    """Counts matches rows where game_mode IS NOT NULL."""
    with SessionLocal() as session:
        return session.query(Match).filter(Match.game_mode.isnot(None)).count()


def get_top_drafters(month: int, year: int, limit: int = 3, min_drafts: int = 5) -> list[dict]:
    """Топ-N драфтеров за заданный месяц/год с минимум min_drafts драфтами."""
    from sqlalchemy import func
    month_start = datetime(year, month, 1, tzinfo=None)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=None)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=None)

    with SessionLocal() as session:
        rows = (
            session.query(
                DraftResult.user_id,
                func.avg(DraftResult.total_score).label("avg_score"),
                func.count(DraftResult.id).label("draft_count"),
            )
            .filter(DraftResult.created_at >= month_start, DraftResult.created_at < month_end)
            .group_by(DraftResult.user_id)
            .having(func.count(DraftResult.id) >= min_drafts)
            .order_by(func.avg(DraftResult.total_score).desc())
            .limit(limit)
            .all()
        )

        user_ids = [r.user_id for r in rows]
        profiles = {
            p.user_id: (p.settings or {})
            for p in session.query(UserProfile).filter(UserProfile.user_id.in_(user_ids)).all()
        }

        result = []
        for rank, row in enumerate(rows, 1):
            s = profiles.get(row.user_id, {})
            result.append({
                "rank": rank,
                "user_id": row.user_id,
                "username": s.get("username"),
                "first_name": s.get("first_name") or f"Игрок {row.user_id}",
                "avg_score": round(row.avg_score, 1),
                "draft_count": row.draft_count,
            })
        return result


# ---------------------------------------------------------------------------
# News broadcast helpers
# ---------------------------------------------------------------------------

def toggle_notify_news(user_id: int) -> bool:
    """Toggles user_profiles.notify_news for the given user and returns the new value.

    Creates a minimal UserProfile row if the user has no profile yet (e.g. they
    sent /news before /start).
    """
    from sqlalchemy.orm.attributes import flag_modified

    with SessionLocal() as session:
        profile = session.get(UserProfile, user_id)
        if profile is None:
            new_value = True
            profile = UserProfile(
                user_id=user_id,
                favorite_heroes=[],
                settings={},
                notify_news=new_value,
            )
            session.add(profile)
        else:
            new_value = not bool(profile.notify_news)
            profile.notify_news = new_value
            flag_modified(profile, "notify_news")
        session.commit()
        return new_value


def get_news_subscribers() -> list[int]:
    """Returns list of user_ids with notify_news=True."""
    with SessionLocal() as session:
        rows = (
            session.query(UserProfile.user_id)
            .filter(UserProfile.notify_news.is_(True))
            .all()
        )
        return [r.user_id for r in rows]


def news_guid_exists(guid: str) -> bool:
    """Returns True if this RSS guid is already in dota_news."""
    with SessionLocal() as session:
        return session.get(DotaNews, guid) is not None


def save_dota_news(
    guid: str,
    title: str,
    link: str,
    published_at: "datetime | None",
) -> None:
    """Inserts a new dota_news row (ignores duplicates via primary key)."""
    with SessionLocal() as session:
        if session.get(DotaNews, guid) is not None:
            return  # already present — skip
        session.add(
            DotaNews(
                guid=guid,
                title=title,
                link=link,
                published_at=published_at,
            )
        )
        session.commit()


def mark_news_notified(guid: str) -> None:
    """Sets dota_news.notified_at = now() for the given guid."""
    with SessionLocal() as session:
        row = session.get(DotaNews, guid)
        if row is not None:
            row.notified_at = datetime.now(timezone.utc)
            session.commit()


def get_latest_news_guids(limit: int = 3) -> list[dict]:
    """Returns the most recent `limit` rows from dota_news (by published_at desc).

    Used in NEWS_TEST_MODE to re-broadcast recent items regardless of notified_at.
    Returns list of dicts with keys: guid, title, link, published_at.
    """
    with SessionLocal() as session:
        rows = (
            session.query(DotaNews)
            .order_by(DotaNews.published_at.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [
            {
                "guid": r.guid,
                "title": r.title,
                "link": r.link,
                "published_at": r.published_at,
            }
            for r in rows
        ]
