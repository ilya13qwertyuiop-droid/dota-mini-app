"""
models.py — All SQLAlchemy ORM models for the Dota Mini App.

Importing this module registers all models with Base (from database.py),
so Alembic can detect the full schema via Base.metadata.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
# DateTime(timezone=True) → TIMESTAMPTZ on PostgreSQL
from sqlalchemy.orm import relationship
from sqlalchemy import JSON

from backend.database import Base


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class Token(Base):
    __tablename__ = "tokens"

    token = Column(String(128), primary_key=True)
    # BigInteger: Telegram user IDs can exceed 32-bit range
    user_id = Column(BigInteger, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)


# ---------------------------------------------------------------------------
# User data
# ---------------------------------------------------------------------------

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(BigInteger, primary_key=True)
    # JSON: stored as json/jsonb on PostgreSQL, as TEXT on SQLite
    favorite_heroes = Column(JSON, nullable=False, default=list)
    settings = Column(JSON, nullable=False, default=dict)

    quiz_results = relationship(
        "QuizResult", back_populates="user", cascade="all, delete-orphan"
    )


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=False, index=True
    )
    result = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("UserProfile", back_populates="quiz_results")


# ---------------------------------------------------------------------------
# Hero matchups cache (proxied from OpenDota)
# ---------------------------------------------------------------------------

class HeroMatchupsCache(Base):
    __tablename__ = "hero_matchups_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hero_id = Column(Integer, nullable=False, index=True)
    opponent_hero_id = Column(Integer, nullable=False)
    games = Column(Integer, nullable=False)
    wins = Column(Integer, nullable=False)
    winrate = Column(Float, nullable=False)
    # Stored as ISO-format string to match the existing cache layer convention
    updated_at = Column(String(32), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "hero_id", "opponent_hero_id", name="uq_hero_matchups_cache_pair"
        ),
    )


# ---------------------------------------------------------------------------
# Stats tables (populated by stats_updater.py)
# ---------------------------------------------------------------------------

class Match(Base):
    __tablename__ = "matches"

    match_id = Column(BigInteger, primary_key=True)
    start_time = Column(Integer, nullable=False)
    duration = Column(Integer)
    patch = Column(String(16))
    avg_rank_tier = Column(Integer)
    rank_bucket = Column(String(16))
    radiant_win = Column(Integer, nullable=False)   # 0 or 1
    # Hero lists stored as JSON strings (json.dumps / json.loads in stats_db.py)
    radiant_heroes = Column(Text, nullable=False)
    dire_heroes = Column(Text, nullable=False)


class HeroMatchup(Base):
    """hero A (smaller ID) vs hero B (larger ID) — cross-team pairs."""
    __tablename__ = "hero_matchups"

    hero_a = Column(Integer, primary_key=True, nullable=False)
    hero_b = Column(Integer, primary_key=True, nullable=False)
    games = Column(Integer, nullable=False, default=0)
    # wins = wins by hero_a (canonical, smaller ID)
    wins = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        # hero_a is covered by the composite PK (leftmost column).
        # Add explicit index on hero_b for the OR-queries in get_hero_matchup_rows().
        {},  # placeholder; index is created in Alembic migration
    )


class HeroSynergy(Base):
    """hero A and hero B — same-team pairs, hero_a < hero_b."""
    __tablename__ = "hero_synergy"

    hero_a = Column(Integer, primary_key=True, nullable=False)
    hero_b = Column(Integer, primary_key=True, nullable=False)
    games = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)


class HeroStat(Base):
    """Per-hero aggregate across all collected matches."""
    __tablename__ = "hero_stats"

    hero_id = Column(Integer, primary_key=True)
    games = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# Feedback (from mini app and bot)
# ---------------------------------------------------------------------------

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    rating = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)
    message = Column(Text, nullable=False)
    source = Column(String(32), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
