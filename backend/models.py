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
    text,
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

    __table_args__ = (
        # Под периодический DELETE протухших токенов (db.cleanup_expired_tokens).
        # Имя совпадает с миграцией 0016 — на свежих БД индекс создаёт
        # create_all, на существующих — миграция (как 0015).
        Index("ix_tokens_expires_at", "expires_at"),
    )


class UsedTelegramInitData(Base):
    """Short-lived replay marker for Telegram WebApp authentication data."""
    __tablename__ = "used_telegram_init_data"

    digest = Column(String(64), primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)


class ApiRateLimitEvent(Base):
    """Persistent rate-limit event shared by all API workers."""
    __tablename__ = "api_rate_limit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(64), nullable=False)
    subject = Column(String(128), nullable=False)
    occurred_at = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_api_rate_limit_scope_subject_ts", "scope", "subject", "occurred_at"),
        Index("ix_api_rate_limit_occurred_at", "occurred_at"),
    )


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
    # Рейтинг игрока в «Битве драфтов» (Elo, _BT_RATING_BASE). Меняется только
    # за бои с живым соперником; бот-бои не влияют. Пол — _BT_RATING_FLOOR (0).
    battle_rating = Column(
        Integer, nullable=False, default=1000, server_default="1000"
    )
    # Сколько ЖИВЫХ боёв завершено (бот-бои не считаются). Первые
    # _BT_CALIBRATION_GAMES — калибровка (большой K, ранг скрыт). Дешёвое
    # состояние калибровки без подсчёта строк draft_battles на каждый чих.
    battle_games_played = Column(
        Integer, nullable=False, default=0, server_default="0"
    )

    __table_args__ = (
        # Лидерборд битвы: WHERE battle_games_played >= N ORDER BY battle_rating
        # DESC — без индекса это seq scan+sort по всей user_profiles на каждый
        # вход в топ (имя = имени в миграции 0022, конвенция 0015/0016).
        Index("ix_user_profiles_battle_lb", "battle_games_played", "battle_rating"),
    )

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


class DraftChallenge(Base):
    """Server-issued enemy draft required for a ranked solo result."""
    __tablename__ = "draft_challenges"

    challenge_id = Column(String(64), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    enemy = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Application locks prevent rerolls; the partial unique index keeps the
        # invariant true even if a future code path forgets that lock.
        Index(
            "uq_draft_challenges_unconsumed_user",
            "user_id",
            unique=True,
            postgresql_where=text("consumed_at IS NULL"),
            sqlite_where=text("consumed_at IS NULL"),
        ),
    )


class MinigameRun(Base):
    """Server-authoritative state for one Higher/Lower run."""
    __tablename__ = "minigame_runs"

    run_id = Column(String(64), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    game = Column(String(16), nullable=False)
    metric = Column(String(16), nullable=False)
    reference_id = Column(Integer, nullable=False)
    reference_value = Column(Float, nullable=False)
    challenger_id = Column(Integer, nullable=False)
    challenger_value = Column(Float, nullable=False)
    round = Column(Integer, nullable=False, default=0, server_default="0")
    streak = Column(Integer, nullable=False, default=0, server_default="0")
    recent_hero_ids = Column(JSON, nullable=False, default=list)
    status = Column(String(12), nullable=False, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index("ix_minigame_runs_user_status", "user_id", "status"),
        Index(
            "uq_minigame_runs_active_user_game",
            "user_id",
            "game",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )


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

    __table_args__ = (
        # get_old_match_ids / get_oldest_match_ids (cleanup) и
        # get_latest_match_patch (ORDER BY start_time DESC LIMIT 1).
        # Имя совпадает с миграцией 0016.
        Index("ix_matches_start_time", "start_time"),
    )


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
        # get_hero_core_items (6 UNION-сканов по hero_id) и strict-режим
        # get_hero_matchup_rows / get_hero_synergy_rows фильтруют по hero_id;
        # без индекса — full-scan ~3M строк. Имя совпадает с миграцией 0016.
        Index("ix_match_players_hero_id_match_id", "hero_id", "match_id"),
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
# Leaderboard moderation
# ---------------------------------------------------------------------------

class BannedUser(Base):
    """Users banned from the draft leaderboard by an admin."""
    __tablename__ = "banned_users"

    user_id = Column(BigInteger, primary_key=True)
    reason = Column(Text, nullable=True)
    banned_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    banned_by = Column(BigInteger, nullable=True)


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

    __table_args__ = (
        # get_analytics_overview: ~50 запросов с фильтром по created_at
        # (DAU по дням + retention-cohorts) + ретеншен-чистка
        # cleanup_old_analytics_events. Имя совпадает с миграцией 0016.
        Index("ix_analytics_events_created_at_user_id", "created_at", "user_id"),
    )


# ---------------------------------------------------------------------------
# Admin broadcast
# ---------------------------------------------------------------------------

class BroadcastJob(Base):
    """State of an admin broadcast (forward-to-all). Persisted so a broadcast
    survives a bot restart and can resume from `cursor` instead of starting
    over. Audience is the user_profiles list ordered by user_id (stable prefix),
    so `cursor` = how many users were already processed.
    """
    __tablename__ = "broadcast_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, nullable=False)
    # Source of the post (chat it was forwarded to the bot from + message id)
    src_chat_id = Column(BigInteger, nullable=False)
    src_message_id = Column(BigInteger, nullable=False)
    # running / done / cancelled
    status = Column(String(16), nullable=False, default="running", server_default="running")
    total = Column(Integer, nullable=False, default=0, server_default="0")
    cursor = Column(Integer, nullable=False, default=0, server_default="0")
    sent = Column(Integer, nullable=False, default=0, server_default="0")
    blocked = Column(Integer, nullable=False, default=0, server_default="0")
    failed = Column(Integer, nullable=False, default=0, server_default="0")
    # Where the live progress message lives (for edits / resume)
    status_chat_id = Column(BigInteger, nullable=True)
    status_message_id = Column(BigInteger, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Teammate finder
# ---------------------------------------------------------------------------

class TeammateProfile(Base):
    """Per-user profile for the teammate-finder feature."""
    __tablename__ = "teammate_profiles"

    user_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), primary_key=True
    )
    # Rank: Рекрут / Страж / Рыцарь / Герой / Легенда / Властелин / Божество / Титан
    rank = Column(String(32), nullable=True, index=True)
    hours = Column(Integer, nullable=True)
    # Array of ints 1..5 (multi-select)
    positions = Column(JSON, nullable=True)
    # Array of strings: ranked / normal / turbo
    game_modes = Column(JSON, nullable=True)
    microphone = Column(Boolean, nullable=False, default=False, server_default="0")
    discord = Column(Boolean, nullable=False, default=False, server_default="0")
    # Array of hero_id (capped at 3 in the app layer)
    favorite_heroes = Column(JSON, nullable=True)
    about = Column(Text, nullable=True)
    # Статус видимости в ленте (миграция 0012, заменил is_searching+TTL):
    #   ready_now / looking_regular / looking_casual — в ленте (по приоритету)
    #   hidden — не в ленте (явно скрыл себя)
    #   NULL   — статус ещё не выбран → юзер увидит обязательный экран выбора
    # Постоянный (не истекает). Присутствие «в сети» показывает last_active_at.
    status = Column(String(20), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    # Когда юзер последний раз делал что-то в miniapp (миграция 0010).
    # Bump'ится в _tm_bump_last_active на каждом authenticated endpoint'е.
    # Используется фронтом для отображения «🟢 в сети» / «был N мин назад».
    # index=True (миграция 0015) — лента сортируется ORDER BY last_active_at DESC.
    last_active_at = Column(DateTime(timezone=True), nullable=True, index=True)
    # Порядковый номер «первопроходца» (миграция 0014). Присваивается при
    # первом заполнении профиля, пока выдано меньше _TM_FOUNDER_CAP.
    # NOT NULL ⇒ юзер — первопроходец (янтарная метка на карточке).
    # NULL     ⇒ обычный юзер. Номер наружу не светим, только факт is_founder.
    founder_number = Column(Integer, nullable=True)


class TeammateRequest(Base):
    """A request from one user to play together with another user."""
    __tablename__ = "teammate_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(
        BigInteger,
        ForeignKey("user_profiles.user_id"),
        nullable=False,
        index=True,
    )
    to_user_id = Column(
        BigInteger,
        ForeignKey("user_profiles.user_id"),
        nullable=False,
        index=True,
    )
    # status: pending / accepted / declined
    status = Column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    # Set to True after the 90-minute follow-up reminder has been delivered.
    review_sent = Column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    # TIMESTAMPTZ — см. миграцию 0008 и комментарий в TeammateProfile выше.
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    accepted_at = Column(DateTime(timezone=True), nullable=True)


class TeammateReview(Base):
    """Post-game review left by one user about another."""
    __tablename__ = "teammate_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=False
    )
    to_user_id = Column(
        BigInteger,
        ForeignKey("user_profiles.user_id"),
        nullable=False,
        index=True,
    )
    request_id = Column(
        Integer, ForeignKey("teammate_requests.id"), nullable=False
    )
    # Array of tag strings selected by the reviewer.
    tags = Column(JSON, nullable=False)
    # TIMESTAMPTZ — см. миграцию 0008.
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class TeammateTag(Base):
    """Per-user aggregate counter: how many times each tag has been applied.

    Positive pool: Бустер, Душа компании, Командный, No tilted, 1x9.
    Negative pool: Токсик, Фидер, AFK, Фотограф, Агент Габена.
    is_positive is stored on every row so a single SELECT can split totals
    into positive vs negative without an external lookup table.
    """
    __tablename__ = "teammate_tags"

    user_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), primary_key=True
    )
    tag = Column(String(64), primary_key=True)
    count = Column(Integer, nullable=False, default=1, server_default="1")
    is_positive = Column(Boolean, nullable=False)

    __table_args__ = (
        # user_id is the leftmost PK column and already gets a composite index,
        # but we keep an explicit single-column index to mirror the migration
        # and the convention used by hero_matchups.ix_hero_matchups_b.
        Index("ix_teammate_tags_user_id", "user_id"),
    )


class TeammateReport(Base):
    """Жалоба одного игрока на другого (Пати). Приватная: отмеченный её не видит,
    публичной метки нет. Админ разбирает и выносит вердикт (бан и т.п.).
    Привязана к accepted-заявке — жаловаться можно только на того, с кем была игра."""
    __tablename__ = "teammate_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=False
    )
    # index=True сам создаёт ix_teammate_reports_reported_user_id. Дублировать его
    # ещё и в __table_args__ нельзя — create_all создаёт индекс дважды и падает
    # «already exists» при старте. Индекс объявляем РОВНО один раз (как в др. моделях).
    reported_user_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=False, index=True
    )
    request_id = Column(
        Integer, ForeignKey("teammate_requests.id"), nullable=False
    )
    reason = Column(String(64), nullable=False)
    text = Column(String(2000), nullable=True)
    status = Column(
        String(16), nullable=False, default="open", server_default="open", index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# ─── Party-finder («Лобби») ───────────────────────────────────────────────


class TeammateLobby(Base):
    """Instant host-led party-finder лобби (3-5 человек).

    Status lifecycle:
      open      — собирается, принимает join'ы
      filled    — все слоты заняты, push разослан, лобби «отплыло»
      disbanded — host явно распустил
      expired   — TTL прошёл (см. teammates_notifier worker)

    needed_positions — позиции, которые host ищет (БЕЗ его собственной).
    Инвариант: party_size == len(needed_positions) + 1, host_position
    не входит в needed_positions.
    """
    __tablename__ = "teammate_lobbies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(
        BigInteger,
        ForeignKey("user_profiles.user_id"),
        nullable=False,
        index=True,
    )
    party_size = Column(Integer, nullable=False)
    # ranked / normal / turbo — те же значения что и в TeammateProfile.game_modes.
    mode = Column(String(16), nullable=False)
    # JSON array of rank strings. NULL = открыто для всех. Обязательно если mode='ranked'.
    rank_filter = Column(JSON, nullable=True)
    needed_positions = Column(JSON, nullable=False)
    host_position = Column(Integer, nullable=False)
    status = Column(
        String(16),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    filled_at = Column(DateTime(timezone=True), nullable=True)


class TeammateLobbySlot(Base):
    """Один слот лобби. user_id NULL = свободный.

    PK (lobby_id, position): ровно один слот на каждую позицию в лобби.
    При создании лобби создаётся party_size слотов: host's-position
    с user_id=host_id, остальные (из needed_positions) с user_id=NULL.

    join: UPDATE … SET user_id=$joiner WHERE lobby_id=$id AND position=$p
                                          AND user_id IS NULL
    leave: UPDATE … SET user_id=NULL WHERE lobby_id=$id AND user_id=$leaver
    """
    __tablename__ = "teammate_lobby_slots"

    lobby_id = Column(
        Integer, ForeignKey("teammate_lobbies.id"), primary_key=True
    )
    position = Column(Integer, primary_key=True)
    # index=True уже создаёт ix_teammate_lobby_slots_user_id. Дублировать его
    # в __table_args__ нельзя — create_all пытается создать индекс дважды и
    # падает «already exists» на рестарте (как было с teammate_reports).
    user_id = Column(
        BigInteger,
        ForeignKey("user_profiles.user_id"),
        nullable=True,
        index=True,
    )
    joined_at = Column(DateTime(timezone=True), nullable=True)


# ─── «Битва драфтов» (PvP-драфтер) ────────────────────────────────────────


class DraftBattle(Base):
    """Комната PvP-драфта. Единственный источник истины о состоянии партии —
    эта строка + журнал ходов draft_battle_actions; воркеры stateless.

    status lifecycle:
      searching — в очереди быстрого матча (виден матчеру своего mode)
      waiting   — дружеский вызов создан, ожидает принятия приглашённым
      drafting  — драфт идёт
      finished  — завершена (result заполнен; при форфейте result.forfeit)
      abandoned — протухла в waiting/searching или отменена хостом

    Оптимистичная блокировка: каждое изменение инкрементит state_version;
    long-poll клиенты ждут version > since. Время хода считает ТОЛЬКО сервер:
    deadline_at = старт хода + базовое время (бан 20с / пик 25с) + остаток
    резерва актора (2 мин на игрока на партию, как bonus time в CM).
    Просроченный дедлайн исполняется лениво (любое чтение/действие) —
    фоновый тикер не нужен.
    """
    __tablename__ = "draft_battles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Короткий инвайт-код (без 0/O/1/I). Уникален среди всех битв.
    code = Column(String(8), nullable=False, unique=True, index=True)
    # 'cm' — с банами (14 банов + 10 пиков, фазы CM 7.34); 'ap' — только 10 пиков.
    mode = Column(String(8), nullable=False)
    status = Column(String(12), nullable=False, default="waiting", index=True)
    host_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=False, index=True
    )
    guest_id = Column(
        BigInteger, ForeignKey("user_profiles.user_id"), nullable=True, index=True
    )
    # Соперник — ИИ-бот (подсаживается, когда живой не нашёлся за таймаут
    # поиска). guest_id при этом NULL; роль бота — всегда 'guest'. Бот ходит
    # лениво на сервере (см. _bt_apply_bot_moves). В онлайн-счётчик не идёт.
    is_bot = Column(Boolean, nullable=False, default=False, server_default="0")
    # Товарищеский матч по вызову друга: не двигает рейтинг, метка в истории.
    is_friendly = Column(Boolean, nullable=False, default=False, server_default="0")
    # Кто ходит первым ('host'/'guest') — жеребьёвка при старте драфта.
    first_pick = Column(String(5), nullable=True)
    turn_index = Column(SmallInteger, nullable=False, default=0)
    state_version = Column(Integer, nullable=False, default=1)
    turn_started_at = Column(DateTime(timezone=True), nullable=True)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    # Остаток дополнительного времени, миллисекунды (см. _BT_RESERVE_MS).
    host_reserve_ms = Column(Integer, nullable=False, default=120000)
    guest_reserve_ms = Column(Integer, nullable=False, default=120000)
    # Стадия расстановки (status='assigning'): каждый игрок приватно
    # раскладывает своих 5 героев по позициям 1-5. {hero_id(str): pos(int)}.
    # NULL = ещё не отправил. Сопернику НЕ сериализуется до финала.
    host_positions = Column(JSON, nullable=True)
    guest_positions = Column(JSON, nullable=True)
    # Финал: {'host': {...compute_draft_score...}, 'guest': {...}, 'penalties',
    # 'final', 'positions'} или {'forfeit': role}.
    result = Column(JSON, nullable=True)
    winner = Column(String(5), nullable=True)   # 'host'/'guest'/'draw'
    # Снимок рейтинга обеих сторон на момент финализации (задел под рейтинг).
    # NULL, пока пересчёт рейтинга не включён; история показывает «до → после».
    host_rating_before = Column(Integer, nullable=True)
    host_rating_after = Column(Integer, nullable=True)
    guest_rating_before = Column(Integer, nullable=True)
    guest_rating_after = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    last_action_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Матчер очереди: WHERE status='searching' AND mode=... ORDER BY id.
        Index("ix_draft_battles_status_mode", "status", "mode"),
    )


class DraftBattleAction(Base):
    """Журнал ходов битвы — источник истины по пикам/банам.

    PK (battle_id, idx) даёт атомарную защиту от двойного хода на один слот
    последовательности (та же идея, что (lobby_id, position) у слотов лобби):
    конкурентная вставка того же idx падает по уникальности, гонка исключена.
    """
    __tablename__ = "draft_battle_actions"

    battle_id = Column(
        Integer, ForeignKey("draft_battles.id"), primary_key=True
    )
    idx = Column(SmallInteger, primary_key=True)   # 0..len(sequence)-1
    actor = Column(String(5), nullable=False)      # 'host'/'guest'
    kind = Column(String(4), nullable=False)       # 'pick'/'ban'
    hero_id = Column(Integer, nullable=False)
    is_auto = Column(Boolean, nullable=False, default=False)  # таймаут-автоход
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class BattlePendingInvite(Base):
    """Последний открытый пользователем дружеский вызов.

    Запись создаётся только после проверки подписанных Telegram initData.
    Она не даёт права войти в бой: /battle/join требует обычную серверную
    сессию и свежую серверную отметку проверки подписки для этого battle_id.
    """
    __tablename__ = "battle_pending_invites"

    # У нового приглашённого ещё может не быть user_profiles, поэтому FK на
    # профиль здесь намеренно нет. Telegram identity подтверждает initData.
    user_id = Column(BigInteger, primary_key=True)
    battle_id = Column(
        Integer, ForeignKey("draft_battles.id"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    # Fresh server-side membership proof for this exact invitation.  A normal
    # API session alone is deliberately insufficient to claim a friend battle.
    subscription_verified_at = Column(DateTime(timezone=True), nullable=True)


# ─── Bot-editable text templates ──────────────────────────────────────────


class BotText(Base):
    """Override-таблица для текстов, которые шлёт бот.

    Двухуровневая модель: если запись с этим key есть — берётся value;
    если нет — fallback на DEFAULT_BOT_TEXTS из backend/bot_texts.py.
    Сброс к дефолту = DELETE row by key.

    Используется через get_text(key, **kwargs) который формирует финальный
    текст подставляя плейсхолдеры {name}, {user_link}, etc.
    """
    __tablename__ = "bot_texts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(256), nullable=False, default="", server_default="")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
