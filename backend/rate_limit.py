"""Database-backed rate limiting shared by all API workers."""

from __future__ import annotations

import hashlib
import time

from sqlalchemy import text

from backend.database import SessionLocal
from backend.models import ApiRateLimitEvent


def _lock_key(scope: str, subject: str) -> int:
    raw = hashlib.sha256(f"{scope}\0{subject}".encode("utf-8")).digest()[:8]
    return int.from_bytes(raw, "big", signed=True)


def check_rate_limit(
    scope: str,
    subject: str | int,
    *,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """Atomically record an event and return ``(allowed, count)``.

    PostgreSQL uses a transaction advisory lock, so separate Uvicorn workers
    cannot race the count/insert boundary. SQLite is used only for local tests.
    """

    scope = str(scope)[:64]
    subject = str(subject)[:128]
    now = time.time()
    cutoff = now - int(window_seconds)
    with SessionLocal() as session:
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": _lock_key(scope, subject)},
            )
        # Bound storage even when an attacker rotates subjects. All configured
        # windows are <= 24h, so older events can never affect a decision.
        if int(now) % 100 == 0:
            session.query(ApiRateLimitEvent).filter(
                ApiRateLimitEvent.occurred_at <= now - 172_800
            ).delete(synchronize_session=False)
        session.query(ApiRateLimitEvent).filter(
            ApiRateLimitEvent.scope == scope,
            ApiRateLimitEvent.subject == subject,
            ApiRateLimitEvent.occurred_at <= cutoff,
        ).delete(synchronize_session=False)
        count = session.query(ApiRateLimitEvent).filter(
            ApiRateLimitEvent.scope == scope,
            ApiRateLimitEvent.subject == subject,
            ApiRateLimitEvent.occurred_at > cutoff,
        ).count()
        if count >= limit:
            session.commit()
            return False, count
        session.add(ApiRateLimitEvent(scope=scope, subject=subject, occurred_at=now))
        session.commit()
        return True, count + 1
