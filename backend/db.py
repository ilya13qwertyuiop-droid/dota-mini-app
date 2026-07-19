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
from backend.models import AnalyticsEvent, BannedUser, BroadcastJob, DotaNews, DraftResult, Feedback, HeroMatchupsCache, Match, QuizResult, Token, UserProfile  # noqa: E402


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

def _token_digest(token: str) -> str:
    """One-way lookup key; a DB snapshot must not contain usable sessions."""
    import hashlib
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token_for_user(user_id: int) -> str:
    """Generates a 24-hour token for the given Telegram user_id."""
    import secrets
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    with SessionLocal() as session:
        token_obj = Token(
            token=_token_digest(token_str), user_id=user_id, expires_at=expires_at
        )
        session.add(token_obj)
        session.commit()

    return token_str


def get_user_id_by_token(token: str) -> int | None:
    """Validates token and returns user_id, or None if missing/expired."""
    if not isinstance(token, str) or not token or len(token) > 256:
        return None
    with SessionLocal() as session:
        token_obj = session.get(Token, _token_digest(token))

        if token_obj is None:
            return None

        if token_obj.expires_at < datetime.utcnow():
            session.delete(token_obj)
            session.commit()
            return None

        return token_obj.user_id


def delete_token(token: str) -> None:
    """Deletes a token (called when it's found to be expired)."""
    if not isinstance(token, str) or not token or len(token) > 256:
        return
    with SessionLocal() as session:
        token_obj = session.get(Token, _token_digest(token))
        if token_obj:
            session.delete(token_obj)
            session.commit()


def cleanup_expired_tokens() -> int:
    """Удаляет все протухшие токены (expires_at < now). Возвращает число
    удалённых строк.

    Каждый /start и каждый refresh_token создают НОВУЮ строку, а протухшие
    удалялись только лениво — при попытке использования. Не использованные
    повторно токены копились вечно. Вызывается периодически из
    teammates_notifier (раз в ~24 ч).

    Cutoff — naive utcnow(): токены пишутся и валидируются через naive
    datetime.utcnow() (см. create_token_for_user / get_user_id_by_token),
    сравниваем в той же шкале. Индекс ix_tokens_expires_at — миграция 0016.
    """
    with SessionLocal() as session:
        deleted = (
            session.query(Token)
            .filter(Token.expires_at < datetime.utcnow())
            .delete(synchronize_session=False)
        )
        session.commit()
    if deleted:
        logger.info("[db] cleanup_expired_tokens: deleted %d expired token(s)", deleted)
    return deleted


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


def get_user_profile_settings(user_id: int) -> dict:
    """Return a detached copy of profile settings for a Telegram user."""

    with SessionLocal() as session:
        profile = session.get(UserProfile, user_id)
        return dict((profile.settings if profile else None) or {})


def upsert_user_profile_settings(
    user_id: int,
    settings_patch: dict,
    *,
    remove_keys: tuple[str, ...] = (),
) -> None:
    """Creates or updates user_profiles.settings fields (shallow merge).

    Used by bot.py /start to persist Telegram profile data without making a
    self-HTTP call to the API server. Equivalent to POST /api/save_telegram_data,
    but runs in-process with a direct DB write.
    """
    from sqlalchemy.orm.attributes import flag_modified

    with SessionLocal() as session:
        profile = session.get(UserProfile, user_id)
        if profile is None:
            initial = dict(settings_patch)
            for key in remove_keys:
                initial.pop(key, None)
            profile = UserProfile(
                user_id=user_id,
                favorite_heroes=[],
                settings=initial,
            )
            session.add(profile)
        else:
            current = dict(profile.settings or {})
            current.update(settings_patch)
            for key in remove_keys:
                current.pop(key, None)
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


def get_top_drafters(month: int, year: int, limit: int = 3) -> list[dict]:
    """Топ-N драфтеров за заданный месяц/год по сумме топ-5 результатов."""
    from sqlalchemy import text
    month_start = datetime(year, month, 1, tzinfo=None)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=None)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=None)

    with SessionLocal() as session:
        rows = session.execute(text("""
            SELECT
                d1.user_id,
                (
                    SELECT COALESCE(SUM(total_score), 0)
                    FROM (
                        SELECT total_score
                        FROM draft_results d2
                        WHERE d2.user_id = d1.user_id
                          AND d2.created_at >= :month_start
                          AND d2.created_at < :month_end
                        ORDER BY total_score DESC
                        LIMIT 5
                    )
                ) AS top5_sum,
                COUNT(*) AS draft_count
            FROM draft_results d1
            WHERE d1.created_at >= :month_start
              AND d1.created_at < :month_end
              AND d1.user_id NOT IN (SELECT user_id FROM banned_users)
            GROUP BY d1.user_id
            ORDER BY top5_sum DESC
            LIMIT :limit
        """), {"month_start": month_start, "month_end": month_end, "limit": limit}).fetchall()

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
                "top5_sum": round(row.top5_sum, 1),
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


def get_all_bot_user_ids() -> list[int]:
    """All user_ids that have a profile (everyone who ever interacted with the
    bot), excluding banned users, ORDERED by user_id. The stable ordering lets
    a broadcast resume from a `cursor` offset after a restart.
    """
    from sqlalchemy import text
    with SessionLocal() as session:
        rows = session.execute(text(
            "SELECT user_id FROM user_profiles "
            "WHERE user_id NOT IN (SELECT user_id FROM banned_users) "
            "ORDER BY user_id"
        )).fetchall()
        return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Broadcast jobs (admin forward-to-all, resumable across restarts)
# ---------------------------------------------------------------------------

def create_broadcast_job(admin_id: int, src_chat_id: int, src_message_id: int,
                         total: int) -> int:
    """Marks any previous running jobs as cancelled, inserts a fresh running
    job and returns its id.
    """
    with SessionLocal() as session:
        session.query(BroadcastJob).filter(
            BroadcastJob.status == "running"
        ).update({"status": "cancelled"})
        job = BroadcastJob(
            admin_id=admin_id, src_chat_id=src_chat_id,
            src_message_id=src_message_id, total=total,
        )
        session.add(job)
        session.commit()
        return job.id


def update_broadcast_job(job_id: int, *, cursor: int, sent: int,
                         blocked: int, failed: int,
                         status: "str | None" = None,
                         status_chat_id: "int | None" = None,
                         status_message_id: "int | None" = None) -> None:
    """Persists progress (and optionally status / status-message coordinates)."""
    fields = {"cursor": cursor, "sent": sent, "blocked": blocked, "failed": failed}
    if status is not None:
        fields["status"] = status
    if status_chat_id is not None:
        fields["status_chat_id"] = status_chat_id
    if status_message_id is not None:
        fields["status_message_id"] = status_message_id
    with SessionLocal() as session:
        session.query(BroadcastJob).filter(BroadcastJob.id == job_id).update(fields)
        session.commit()


def get_active_broadcast_job() -> "dict | None":
    """Returns the most recent running job as a plain dict, or None."""
    with SessionLocal() as session:
        job = (
            session.query(BroadcastJob)
            .filter(BroadcastJob.status == "running")
            .order_by(BroadcastJob.id.desc())
            .first()
        )
        if job is None:
            return None
        return {
            "id": job.id, "admin_id": job.admin_id,
            "src_chat_id": job.src_chat_id, "src_message_id": job.src_message_id,
            "total": job.total, "cursor": job.cursor,
            "sent": job.sent, "blocked": job.blocked, "failed": job.failed,
            "status_chat_id": job.status_chat_id,
            "status_message_id": job.status_message_id,
        }


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


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def log_event(event: str, user_id: int | None) -> None:
    """Пишет одно событие в analytics_events. Best-effort: ошибки логируются,
    но никогда не пробрасываются — аналитика не должна валить юзер-флоу.

    `event` — snake_case идентификатор (например, 'bot_start', 'page_drafter').
    Обрезается до 64 символов (под колонку). `user_id` может быть None для
    анонимных событий (пока не используется, но допустимо схемой)."""
    if not event:
        return
    try:
        with SessionLocal() as session:
            session.add(AnalyticsEvent(event=event[:64], user_id=user_id))
            session.commit()
    except Exception as e:
        logger.warning("[analytics] log_event(%s, %s) failed: %s", event, user_id, e)


# ---------------------------------------------------------------------------
# Leaderboard ban management
# ---------------------------------------------------------------------------

def is_user_banned(user_id: int) -> bool:
    with SessionLocal() as session:
        return session.get(BannedUser, user_id) is not None


def get_banned_user_ids() -> set[int]:
    with SessionLocal() as session:
        return {row.user_id for row in session.query(BannedUser.user_id).all()}


def ban_user(user_id: int, banned_by: int | None = None, reason: str | None = None) -> bool:
    """Adds user_id to banned_users. Returns True if newly banned, False if already banned."""
    with SessionLocal() as session:
        existing = session.get(BannedUser, user_id)
        if existing is not None:
            return False
        session.add(BannedUser(
            user_id=user_id,
            reason=reason,
            banned_at=datetime.now(timezone.utc),
            banned_by=banned_by,
        ))
        session.commit()
        return True


def unban_user(user_id: int) -> bool:
    """Removes user_id from banned_users. Returns True if removed, False if not banned."""
    with SessionLocal() as session:
        existing = session.get(BannedUser, user_id)
        if existing is None:
            return False
        session.delete(existing)
        session.commit()
        return True


def find_user_id_by_username(username: str) -> int | None:
    """Finds user_id by Telegram @username stored in user_profiles.settings.

    Case-insensitive; @-prefix is stripped. Returns None if not found.
    """
    handle = username.lstrip("@").strip().lower()
    if not handle:
        return None
    with SessionLocal() as session:
        profiles = (
            session.query(UserProfile)
            .filter(UserProfile.settings.isnot(None))
            .all()
        )
        for p in profiles:
            s = p.settings or {}
            uname = s.get("username")
            if isinstance(uname, str) and uname.lstrip("@").lower() == handle:
                return p.user_id
    return None


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
