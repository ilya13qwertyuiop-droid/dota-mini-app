"""
models.py — All SQLAlchemy ORM models for the Dota Mini App.

Importing this module registers all models with Base (from database.py),
so Alembic can detect the full schema via Base.metadata.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
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
    # Timestamp of first profile creation; NULL for rows predating this column
    created_at = Column(
        DateTime,
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
    # Opt-in flag for Dota 2 news broadcast (toggled via /news bot command)
    notify_news = Column(Boolean, nullable=False, default=False, server_default="0")

    quiz_results = relationship(
        "QuizResult", back_populates="user", cascade="all, delete-orphan"
    )
    draft_results = relationship(
        "DraftResult", back_populates="user", cascade="all, delete-orphan"
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
        index=True,  # count_active_users_30d() range-scan; get_last_quiz_result() ORDER BY
    )

    user = relationship("UserProfile", back_populates="quiz_results")


class DraftResult(Base):
    __tablename__ = "draft_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=False, index=True
    )
    total_score = Column(Float, nullable=False)
    ally_heroes = Column(JSON, nullable=True)
    enemy_heroes = Column(JSON, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = relationship("UserProfile", back_populates="draft_results")


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
    # OpenDota game_mode codes: 1=All Pick, 22=Ranked All Pick, 23=Turbo, etc.
    game_mode = Column(SmallInteger)
    # OpenDota lobby_type codes: 0=public, 7=ranked, etc.
    lobby_type = Column(SmallInteger)
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
        # hero_a is the leftmost PK column — already indexed.
        # hero_b needs its own index for the OR-queries in get_hero_matchup_rows().
        Index("ix_hero_matchups_hero_b", "hero_b"),
    )


class HeroSynergy(Base):
    """hero A and hero B — same-team pairs, hero_a < hero_b."""
    __tablename__ = "hero_synergy"

    hero_a = Column(Integer, primary_key=True, nullable=False)
    hero_b = Column(Integer, primary_key=True, nullable=False)
    games = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        # hero_a covered by composite PK; hero_b needs explicit index for OR-queries.
        Index("ix_hero_synergy_hero_b", "hero_b"),
    )


class HeroStat(Base):
    """Per-hero aggregate across all collected matches."""
    __tablename__ = "hero_stats"

    hero_id = Column(Integer, primary_key=True)
    games = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)


class HeroAbilityBuild(Base):
    """Per-hero skill build aggregate (first 18 ability upgrades, levels 1-18)."""
    __tablename__ = "hero_ability_builds"

    hero_id = Column(Integer, primary_key=True, nullable=False)
    # JSON array string of first 18 ability_id values in upgrade order
    ability_ids = Column(Text, primary_key=True, nullable=False)
    wins = Column(Integer, nullable=False, default=0)
    games = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=True)


class AppCache(Base):
    """Generic key-value store for large JSON blobs cached by builds_updater.

    Separate from app_settings (small text values) — this table stores full
    OpenDota API responses (abilities.json, items constants, etc.).
    """
    __tablename__ = "app_cache"

    key = Column(Text, primary_key=True)
    data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class HeroBuildsCache(Base):
    """Pre-built Build tab data per hero, refreshed weekly by builds_updater.

    Stores facets, human-readable talents, start_game_items for each hero.
    The API endpoint merges this with live stats (ability_build, core_items).
    """
    __tablename__ = "hero_builds_cache"

    hero_id = Column(Integer, primary_key=True)
    build_data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class MatchPlayer(Base):
    """Per-player record for each match (populated by stats_updater when FETCH_MATCH_DETAILS=1).

    Rows for matches saved before this table existed will be inserted by the
    backfill worker (BACKFILL_ENABLED=1).  All extended stats columns are
    nullable so that a basic row (hero_id / side) can be written without
    immediately having the full details.
    """
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # No ForeignKey constraint — delete_matches_and_recalculate handles
    # match_players cleanup explicitly, avoiding cascade issues on SQLite.
    match_id = Column(BigInteger, nullable=False, index=True)
    hero_id = Column(Integer, nullable=False)
    player_slot = Column(Integer, nullable=False)   # 0-127 radiant, 128-255 dire
    is_radiant = Column(Integer, nullable=False)    # 0 or 1

    # Extended stats — NULL for records written before this migration
    lane = Column(SmallInteger)          # 1=safe, 2=mid, 3=off, 4=jungle
    lane_role = Column(SmallInteger)     # OpenDota internal lane_role
    gpm = Column(Integer)                # gold_per_min
    xpm = Column(Integer)                # xp_per_min
    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    hero_damage = Column(Integer)
    tower_damage = Column(Integer)
    obs_placed = Column(Integer)         # observer wards placed (NULL if not in data)
    sen_placed = Column(Integer)         # sentry wards placed   (NULL if not in data)

    # Top-3 core item IDs (cheap consumables filtered out); NULL = unknown
    item0 = Column(Integer)
    item1 = Column(Integer)
    item2 = Column(Integer)

    __table_args__ = (
        UniqueConstraint("match_id", "player_slot", name="uq_match_player"),
    )


# ---------------------------------------------------------------------------
# News broadcast
# ---------------------------------------------------------------------------

class DotaNews(Base):
    """RSS entries from the Dota 2 Steam news feed.

    Each row is inserted when a new guid is seen; notified_at is set after the
    broadcast to all notify_news=True users has been sent.
    """
    __tablename__ = "dota_news"

    guid = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    link = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Feedback (from mini app and bot)
# ---------------------------------------------------------------------------

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    username = Column(String(64), nullable=True)
    rating = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)
    message = Column(Text, nullable=False)
    source = Column(String(32), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Analytics events
# ---------------------------------------------------------------------------

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event = Column(String(64), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
