"""
stats_updater.py — Background worker for collecting Dota 2 match statistics.

Run as a standalone process:
    python -m backend.stats_updater          # from project root
    python backend/stats_updater.py          # also works

Environment variables (all optional, sensible defaults):
    OPENDOTA_API_KEY          — paid API key (up to 3000 req/min)
    POLL_INTERVAL_MINUTES     — how often to poll for new matches (default: 15)
    MAX_REQUESTS_PER_MINUTE   — self-imposed rate limit (default: 30)
    MAX_MATCHES               — maximum matches to keep in DB (default: 300000)
    DAYS_TO_KEEP              — matches older than this are deleted (default: 90)
    CLEANUP_INTERVAL_HOURS    — how often to run cleanup job (default: 24)
    MAX_MATCHES_PER_CYCLE     — max new matches processed per poll cycle (default: 50)
    FETCH_MATCH_DETAILS       — MUST be "1" to collect hero data.
                                 publicMatches does not include real hero IDs
                                 (radiant_team/dire_team are zeroed in the API response).
                                 When set to "1": for each new match_id found in
                                 publicMatches, fetches /matches/{id} to get players
                                 and hero_id values. Default: "0" (no data collected).
    USE_EXPLORER              — set to "1" to enable the OpenDota Explorer polling loop.
                                 Queries /api/explorer with SQL against public_matches to
                                 get recent ranked match IDs, then fetches /matches/{id}
                                 for each new one.  Runs as a background asyncio task
                                 parallel to the publicMatches loop.
                                 Default: "0" (disabled).
    EXPLORER_INTERVAL_SECONDS — how often the explorer loop polls, in seconds.
                                 Default: 1800 (30 minutes).
    EXPLORER_MAX_IDS_PER_QUERY — max match IDs returned by one Explorer SQL
                                 query (LIMIT clause).  Default: 100.
                                 Reduce to 20–30 for a lighter request budget.
    STATS_BOOTSTRAP_MODE      — set to "1" or "true" to enable aggressive settings
                                 for rapid initial DB population (default: "0").
                                 Overrides POLL_INTERVAL_MINUTES → 5,
                                 MAX_MATCHES_PER_CYCLE → 100,
                                 MAX_REQUESTS_PER_MINUTE → 200.
                                 Peak API rate: ~200 req/min during the burst window
                                 (~30 s), then idle — well under the 3000 req/min limit.

Game-mode filter (see ALLOWED_GAME_MODE_PAIRS in backend/config.py):
    Only matches whose (game_mode, lobby_type) pair is in the allow-list are
    written to the DB.  Default: {(22, 7)} = Ranked All Pick only.
    Matches with NULL game_mode or lobby_type, or any other pair (Turbo=23,
    unranked AP=(1,0), Ability Draft=18, etc.) are dropped before any DB write.

Backfill of legacy matches:
    ENABLE_BACKFILL_OLD_MATCHES is hardcoded to False.
    The backfill functions are preserved in this file but not called.
    To run a one-off legacy backfill, set the flag to True and restart.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running as "python backend/stats_updater.py" from project root
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env if present (best-effort; fails silently if dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from backend.config import ALLOWED_GAME_MODE_PAIRS, MIN_MATCH_DURATION_SECONDS
from backend.opendota_client import get_public_matches, get_match_details, get_explorer_match_rows
from backend.stats_db import (
    init_stats_tables,
    match_exists,
    save_match_and_update_aggregates,
    get_matches_count,
    get_old_match_ids,
    get_oldest_match_ids,
    delete_matches_and_recalculate,
    get_match_ids_needing_backfill,
    update_match_players_backfill,
    count_matches_needing_backfill,
    get_app_setting,
    set_app_setting,
    get_app_cache_value,
    set_app_cache_value,
    set_hero_build_cache,
    get_hero_core_items,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

POLL_INTERVAL_MINUTES: int = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))
MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
MAX_MATCHES: int = int(os.getenv("MAX_MATCHES", "300000"))
DAYS_TO_KEEP: int = int(os.getenv("DAYS_TO_KEEP", "90"))
CLEANUP_INTERVAL_HOURS: int = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))
MAX_MATCHES_PER_CYCLE: int = int(os.getenv("MAX_MATCHES_PER_CYCLE", "50"))
FETCH_MATCH_DETAILS: bool = os.getenv("FETCH_MATCH_DETAILS", "0") == "1"

# Explorer polling loop (alternative to publicMatches path)
USE_EXPLORER: bool = os.getenv("USE_EXPLORER", "0") == "1"
EXPLORER_INTERVAL_SECONDS: int = int(os.getenv("EXPLORER_INTERVAL_SECONDS", "1800"))
EXPLORER_MAX_IDS_PER_QUERY: int = int(os.getenv("EXPLORER_MAX_IDS_PER_QUERY", "100"))

# ---------------------------------------------------------------------------
# Bootstrap mode — overrides for rapid initial DB population
# ---------------------------------------------------------------------------

_bootstrap_raw = os.getenv("STATS_BOOTSTRAP_MODE", "0").strip().lower()
STATS_BOOTSTRAP_MODE: bool = _bootstrap_raw in ("1", "true", "yes")

if STATS_BOOTSTRAP_MODE:
    # Aggressive values: 101 API calls × (60 / 200) s ≈ 30 s burst per cycle,
    # then ~270 s idle. Peak rate: 200 req/min — far below the 3000 req/min limit.
    POLL_INTERVAL_MINUTES = 5
    MAX_MATCHES_PER_CYCLE = 100
    MAX_REQUESTS_PER_MINUTE = 200

# ---------------------------------------------------------------------------
# Game-mode allow-list (imported from config.py)
# ---------------------------------------------------------------------------
# ALLOWED_GAME_MODE_PAIRS is imported from backend.config.
# Currently: {(22, 7)} — Ranked All Pick only.
# Both game_mode AND lobby_type must be non-NULL and in the set for a match
# to be written to the DB.  Edit config.py to add/remove modes.

# ---------------------------------------------------------------------------
# Backfill of legacy matches — DISABLED
# ---------------------------------------------------------------------------

# Set to True only for a one-off manual run to backfill pre-existing matches.
# Under normal operation this must stay False so the worker never issues
# extra API calls to /matches/{id} for already-saved match rows.
ENABLE_BACKFILL_OLD_MATCHES: bool = False

# Parameters used when backfill is manually re-enabled (kept for reference).
BACKFILL_MAX_MATCHES_PER_RUN: int = 150
BACKFILL_SLEEP_BETWEEN_CALLS: float = 0.7

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stats_updater")


# ---------------------------------------------------------------------------
# Rate limiter — minimum delay between API calls
# ---------------------------------------------------------------------------

class RateLimiter:
    """Enforces a minimum inter-request delay based on max_per_minute."""

    def __init__(self, max_per_minute: int) -> None:
        self._min_delay = 60.0 / max(max_per_minute, 1)
        self._last_call: float = 0.0

    async def acquire(self) -> None:
        """Sleeps if needed so we never exceed max_per_minute."""
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_delay:
            await asyncio.sleep(self._min_delay - elapsed)
        self._last_call = time.monotonic()


_rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)


# ---------------------------------------------------------------------------
# Rank bucket mapping
# ---------------------------------------------------------------------------

def _rank_bucket_for_tier(avg_rank_tier: int | None) -> str:
    """
    Maps OpenDota avg_rank_tier (major * 10 + minor, e.g. 55 = Legend V)
    to a coarse named bucket for rank-stratified analysis.

    Boundaries:
      None / 0    → "unknown"
      1  – 20     → "low"       (Herald)
      21 – 35     → "mid"       (Guardian + Crusader)
      36 – 50     → "high"      (Archon)
      51 – 60     → "very_high" (Legend)
      61+         → "immortal"  (Ancient + Divine + Immortal)
    """
    if not avg_rank_tier:
        return "unknown"
    if avg_rank_tier <= 20:
        return "low"
    if avg_rank_tier <= 35:
        return "mid"
    if avg_rank_tier <= 50:
        return "high"
    if avg_rank_tier <= 60:
        return "very_high"
    return "immortal"


# ---------------------------------------------------------------------------
# Item filtering
# ---------------------------------------------------------------------------

# Item IDs that are cheap consumables / starting items and should NOT count
# as a hero's "core" build.  Based on OpenDota numeric item IDs.
_JUNK_ITEM_IDS: frozenset[int] = frozenset({
    0,    # empty slot
    44,   # clarity potion
    45,   # tango
    46,   # healing salve
    42,   # observer ward
    43,   # sentry ward
    185,  # smoke of deceit
    145,  # town portal scroll
    244,  # wind lace
    46,   # healing salve (duplicate guard)
})


# ---------------------------------------------------------------------------
# Match parsing helpers
# ---------------------------------------------------------------------------

def _extract_player_stats(player: dict) -> dict:
    """Extracts per-player stats from a full /matches/{id} player record.

    Picks up to 6 "core" items from slots item_0..item_5 by filtering out
    cheap consumables defined in _JUNK_ITEM_IDS.  Missing or 0-valued slots
    are also skipped.  The result is padded with None up to 6 entries.

    "Одиночные" поля игрока (scalar stats):
      economy  — gpm, xpm, last_hits, denies, net_worth
      combat   — kills, deaths, assists, hero_damage, tower_damage, hero_healing
      support  — obs_placed, sen_placed
      items    — item0..item5 (core build, junk filtered)

    Потенциальные временные ряды (lh_t, dn_t, gold_t, xp_t, net_worth_t)
    намеренно не включены сюда — они выносятся в отдельную структуру/таблицу.
    """
    raw_items = [player.get(f"item_{i}", 0) or 0 for i in range(6)]
    core_items: list[int | None] = [
        iid for iid in raw_items if iid and iid not in _JUNK_ITEM_IDS
    ][:6]
    while len(core_items) < 6:
        core_items.append(None)

    slot = player.get("player_slot", 128)
    return {
        # --- identity ---
        "hero_id":      player.get("hero_id"),
        "player_slot":  slot,
        "is_radiant":   1 if slot < 128 else 0,
        # --- lane / role ---
        "lane":         player.get("lane"),
        "lane_role":    player.get("lane_role"),
        # --- economy ---
        "gpm":          player.get("gold_per_min"),
        "xpm":          player.get("xp_per_min"),
        "last_hits":    player.get("last_hits"),
        "denies":       player.get("denies"),
        "net_worth":    player.get("net_worth"),
        # --- combat ---
        "kills":        player.get("kills"),
        "deaths":       player.get("deaths"),
        "assists":      player.get("assists"),
        "hero_damage":  player.get("hero_damage"),
        "tower_damage": player.get("tower_damage"),
        "hero_healing": player.get("hero_healing"),
        # --- support ---
        "obs_placed":   player.get("obs_placed"),
        "sen_placed":   player.get("sen_placed"),
        # --- items (core build, junk filtered) ---
        "item0":        core_items[0],
        "item1":        core_items[1],
        "item2":        core_items[2],
        "item3":        core_items[3],
        "item4":        core_items[4],
        "item5":        core_items[5],
        # --- ability build (first 30 upgrades, covers levels 1-25 including all talents) ---
        "ability_upgrades": (player.get("ability_upgrades_arr") or [])[:30],
    }


def _extract_player_timeline(player: dict, duration_sec: int) -> list[dict]:
    """Builds per-10-minute snapshot rows from OpenDota time-series arrays.

    OpenDota returns cumulative arrays indexed by minute:
      lh_t[m]   — total last hits at minute m
      dn_t[m]   — total denies at minute m
      gold_t[m] — cumulative gold at minute m  → used to compute GPM
      xp_t[m]   — cumulative XP at minute m   → used to compute XPM

    We sample every 10th minute up to min(match_duration_minutes, array_len-1)
    and compute instantaneous GPM/XPM as cumulative_value / minute.

    Потенциальные временные ряды (отдельная структура, не scalar stats):
    эта функция намеренно отделена от _extract_player_stats.
    """
    lh_t   = player.get("lh_t")        or []
    dn_t   = player.get("dn_t")        or []
    gold_t = player.get("gold_t")      or []
    xp_t   = player.get("xp_t")        or []
    nw_t   = player.get("net_worth_t") or []

    slot = player.get("player_slot", 128)

    # If OpenDota hasn't parsed the replay yet, all arrays are absent.
    # Log a debug message so this silence is visible in journalctl.
    max_data_len = max(len(lh_t), len(dn_t), len(gold_t), len(xp_t), len(nw_t), 0)
    if max_data_len == 0:
        logger.debug(
            "[timeline] slot=%d: lh_t/gold_t/xp_t arrays absent (replay not parsed yet)",
            slot,
        )
        return []

    # Maximum minute we can meaningfully report.
    # When duration_sec is 0 (API returned None → caller used 0 as fallback),
    # trust the array lengths instead of clamping to 0.
    if duration_sec > 0:
        max_minute = min(duration_sec // 60, max_data_len - 1)
    else:
        max_minute = max_data_len - 1
    # Round down to the nearest multiple of 10
    max_minute_10 = (max_minute // 10) * 10

    rows: list[dict] = []
    for m in range(10, max_minute_10 + 1, 10):
        lh  = lh_t[m]   if m < len(lh_t)   else None
        dn  = dn_t[m]   if m < len(dn_t)   else None
        # GPM/XPM = cumulative value / elapsed minutes (instantaneous rate)
        gpm = round(gold_t[m] / m) if m < len(gold_t) and gold_t[m] is not None else None
        xpm = round(xp_t[m]   / m) if m < len(xp_t)  and xp_t[m]  is not None else None
        nw  = nw_t[m]   if m < len(nw_t)   else None
        rows.append({
            "player_slot": slot,
            "minute":      m,
            "lh":          lh,
            "dn":          dn,
            "gpm":         gpm,
            "xpm":         xpm,
            "net_worth":   nw,
        })
    return rows


def _parse_public_match(match: dict) -> dict | None:
    """
    Extracts basic metadata from a publicMatches entry.

    NOTE: radiant_team/dire_team from publicMatches are not used — the API
    returns zeroed lists ([0,0,0,0,0]) for those fields. Hero data is only
    available via get_match_details().

    Returns a dict with {match_id, start_time, radiant_win, avg_rank_tier},
    or None if match_id is missing.
    """
    match_id = match.get("match_id")
    if not match_id:
        return None
    return {
        "match_id": match_id,
        "start_time": match.get("start_time") or 0,
        "radiant_win": bool(match.get("radiant_win", False)),
        "avg_rank_tier": match.get("avg_rank_tier"),
    }


def _parse_match_details(match: dict) -> dict | None:
    """
    Extracts hero data and match result from a full /matches/{match_id} response.

    Hero assignment uses player_slot:
      player_slot < 128  → Radiant
      player_slot >= 128 → Dire

    Returns None (with a warning log) when:
      - total player count != 10
      - any player has hero_id == 0 or None
      - the radiant/dire split doesn't produce exactly 5+5
    """
    match_id = match.get("match_id")
    if not match_id:
        return None

    players = match.get("players") or []

    if len(players) != 10:
        logger.warning(
            "[updater] match %d: expected 10 players, got %d — skipping",
            match_id, len(players),
        )
        return None

    missing_hero = sum(1 for p in players if not p.get("hero_id"))
    if missing_hero:
        logger.warning(
            "[updater] match %d: %d player(s) have hero_id=0/None — skipping",
            match_id, missing_hero,
        )
        return None

    # Use player_slot to assign sides; skip players whose slot is absent
    radiant_heroes = [
        p["hero_id"]
        for p in players
        if p.get("player_slot") is not None and p["player_slot"] < 128
    ]
    dire_heroes = [
        p["hero_id"]
        for p in players
        if p.get("player_slot") is not None and p["player_slot"] >= 128
    ]

    if len(radiant_heroes) != 5 or len(dire_heroes) != 5:
        logger.warning(
            "[updater] match %d: unexpected team split radiant=%d dire=%d "
            "(player_slot missing or out of range) — skipping",
            match_id, len(radiant_heroes), len(dire_heroes),
        )
        return None

    patch_val = match.get("patch")
    avg_rank_tier = match.get("avg_rank_tier")
    bucket = _rank_bucket_for_tier(avg_rank_tier)

    # Diagnostic: details endpoint often omits avg_rank_tier even when
    # /publicMatches had it. Logged at DEBUG to avoid INFO spam;
    # the fallback result is logged at INFO in fetch_and_process_matches.
    if avg_rank_tier is None:
        logger.debug(
            "[diag] parse_match_details: match=%s avg_rank_tier=None (pre-fallback) → bucket=%s",
            match_id, bucket,
        )

    # Per-player extended stats (used by match_players table)
    player_records = [_extract_player_stats(p) for p in players]

    # Per-player 10-minute timeline snapshots (used by match_player_timeline table).
    # duration may be None for very fresh matches; fall back to 0 so
    # _extract_player_timeline returns an empty list rather than crashing.
    duration_sec = match.get("duration") or 0
    players_timeline: list[dict] = []
    for p in players:
        players_timeline.extend(_extract_player_timeline(p, duration_sec))

    return {
        "match_id": match_id,
        "start_time": match.get("start_time") or 0,
        "duration": match.get("duration"),
        "patch": str(patch_val) if patch_val is not None else None,
        "avg_rank_tier": avg_rank_tier,
        "rank_bucket": bucket,
        "game_mode": match.get("game_mode"),    # e.g. 1=AllPick, 22=Ranked, 23=Turbo
        "lobby_type": match.get("lobby_type"), # e.g. 0=public, 7=ranked
        "radiant_win": bool(match.get("radiant_win", False)),
        "radiant_heroes": radiant_heroes,
        "dire_heroes": dire_heroes,
        "players": player_records,
        "players_timeline": players_timeline,
    }


# ---------------------------------------------------------------------------
# Single-match processing — shared by publicMatches and explorer paths
# ---------------------------------------------------------------------------

async def process_single_match(
    match_id: int,
    fallback_avg_rank_tier: int | None = None,
    source: str = "unknown",
) -> bool:
    """Fetches /matches/{id}, parses, filters, and saves one match.

    Used by both fetch_and_process_matches (publicMatches path) and
    explorer_loop (explorer path) so the logic is never duplicated.

    The caller is responsible for calling match_exists() beforehand and
    skipping already-known IDs — this function assumes the match is new.

    fallback_avg_rank_tier — avg_rank_tier from the outer API response
      (publicMatches entry); used when /matches/{id} omits the field.
    source — label for log messages: "publicMatches" or "explorer".

    Returns True if the match was saved, False otherwise (reason is logged).
    """
    await _rate_limiter.acquire()
    try:
        details = await get_match_details(match_id)
    except Exception as exc:
        logger.warning("[%s] HTTP error for match %d: %s", source, match_id, exc)
        return False

    parsed = _parse_match_details(details)
    if parsed is None:
        return False  # reason already logged by _parse_match_details

    game_mode = parsed.get("game_mode")
    lobby_type = parsed.get("lobby_type")
    if game_mode is None or lobby_type is None:
        logger.info(
            "[%s] match %d: skipped (game_mode=%s or lobby_type=%s is None)",
            source, match_id, game_mode, lobby_type,
        )
        return False
    if (game_mode, lobby_type) not in ALLOWED_GAME_MODE_PAIRS:
        logger.info(
            "[%s] match %d: skipped (game_mode=%s, lobby_type=%s) not in allowed pairs",
            source, match_id, game_mode, lobby_type,
        )
        return False

    # /matches/{id} often omits avg_rank_tier; fall back to outer source value.
    if parsed["avg_rank_tier"] is None and fallback_avg_rank_tier is not None:
        parsed["avg_rank_tier"] = fallback_avg_rank_tier
        parsed["rank_bucket"] = _rank_bucket_for_tier(fallback_avg_rank_tier)

    try:
        save_match_and_update_aggregates(**parsed)
        logger.info(
            "[%s] saved match %d (game_mode=%d, lobby_type=%d, rank=%s)",
            source, match_id, game_mode, lobby_type, parsed.get("rank_bucket", "unknown"),
        )
        return True
    except Exception as exc:
        logger.error("[%s] DB error saving match %d: %s", source, match_id, exc)
        return False


# ---------------------------------------------------------------------------
# Backfill worker — fill match_players for pre-existing matches
# ---------------------------------------------------------------------------

async def backfill_match_player_stats(limit_matches: int | None = None) -> None:
    """Fetches /matches/{id} for matches that have no match_players rows yet
    and writes per-player stats to the DB.

    Called once per main-loop cycle when BACKFILL_ENABLED=1.  Uses the same
    shared rate limiter as the normal polling path so it never creates a
    second, uncontrolled request stream.

    An extra BACKFILL_SLEEP_BETWEEN_CALLS delay (default 0.7 s) is inserted
    after each API call to leave headroom for the normal poller.
    """
    if not FETCH_MATCH_DETAILS:
        logger.warning(
            "[backfill] FETCH_MATCH_DETAILS is disabled — cannot fetch player "
            "details; skipping backfill"
        )
        return

    limit = limit_matches if limit_matches is not None else BACKFILL_MAX_MATCHES_PER_RUN
    match_ids = get_match_ids_needing_backfill(limit)

    if not match_ids:
        remaining = count_matches_needing_backfill()
        if remaining == 0:
            logger.info("[backfill] All matches have player stats — nothing to backfill")
        return

    remaining_before = count_matches_needing_backfill()
    logger.info(
        "[backfill] Starting batch: %d matches in this run | ~%d remaining total",
        len(match_ids), remaining_before,
    )

    updated = 0
    failed = 0

    for match_id in match_ids:
        await _rate_limiter.acquire()
        try:
            details = await get_match_details(match_id)
        except Exception as exc:
            logger.warning("[backfill] HTTP error for match %d: %s", match_id, exc)
            failed += 1
            continue

        parsed = _parse_match_details(details)
        if parsed is None or not parsed.get("players"):
            logger.debug("[backfill] match %d: skipped (incomplete/invalid details)", match_id)
            failed += 1
            continue

        try:
            update_match_players_backfill(match_id, parsed["players"])
            updated += 1
        except Exception as exc:
            logger.error("[backfill] DB error for match %d: %s", match_id, exc)
            failed += 1
            continue

        # Extra breathing room so backfill doesn't crowd out the normal poller
        if BACKFILL_SLEEP_BETWEEN_CALLS > 0:
            await asyncio.sleep(BACKFILL_SLEEP_BETWEEN_CALLS)

    remaining_after = count_matches_needing_backfill()
    logger.info(
        "[backfill] Batch done: +%d updated | %d failed | ~%d still remaining",
        updated, failed, remaining_after,
    )


# ---------------------------------------------------------------------------
# Core polling logic
# ---------------------------------------------------------------------------

async def fetch_and_process_matches() -> None:
    """
    One polling cycle via /publicMatches:
      1. Fetch recent public match IDs from /publicMatches (1 request).
      2. If FETCH_MATCH_DETAILS is disabled: log a warning and return.
      3. For each new match_id, delegate to process_single_match() which
         handles the /matches/{id} call, filtering, and DB write.
    """
    if not FETCH_MATCH_DETAILS:
        logger.warning(
            "[publicMatches] FETCH_MATCH_DETAILS=0 — path disabled. "
            "Set FETCH_MATCH_DETAILS=1 to enable."
        )
        return

    await _rate_limiter.acquire()
    try:
        raw_matches = await get_public_matches()
    except Exception as exc:
        logger.error("[publicMatches] Failed to fetch: %s", exc)
        return

    logger.info("[publicMatches] returned %d entries", len(raw_matches))

    saved = 0
    skip_existing = 0
    skip_other = 0

    for raw in raw_matches[:MAX_MATCHES_PER_CYCLE]:
        basic = _parse_public_match(raw)
        if basic is None:
            continue

        match_id = basic["match_id"]

        if match_exists(match_id):
            skip_existing += 1
            continue

        ok = await process_single_match(
            match_id,
            fallback_avg_rank_tier=basic.get("avg_rank_tier"),
            source="publicMatches",
        )
        if ok:
            saved += 1
        else:
            skip_other += 1

    logger.info(
        "[publicMatches] cycle done: +%d saved | %d existed | %d skipped",
        saved, skip_existing, skip_other,
    )


# ---------------------------------------------------------------------------
# Explorer loop — alternative match ingestion via /api/explorer SQL
# ---------------------------------------------------------------------------

async def explorer_loop() -> None:
    """Background task: polls OpenDota Explorer for ranked match IDs.

    Runs independently of the publicMatches loop as an asyncio.Task started
    in main().  Both paths share the same _rate_limiter so their combined
    /matches/{id} call rate never exceeds MAX_REQUESTS_PER_MINUTE.

    Flow per cycle:
      1. For each (game_mode, lobby_type) pair in ALLOWED_GAME_MODE_PAIRS:
         call GET /api/explorer with SQL returning match_id, duration,
         avg_rank_tier.  On the first run: ORDER BY match_id DESC (newest
         first) to initialise the pointer.  On subsequent runs:
         WHERE match_id > last_seen ORDER BY match_id ASC (incremental).
      2. Update the per-pair "last seen match_id" pointer so the next cycle
         only fetches matches that appeared after this one.
      3. Skip rows whose duration is already known to be < MIN_MATCH_DURATION_SECONDS
         without issuing a /matches/{id} request.
      4. For each remaining new match_id, call process_single_match().
      5. Sleep EXPLORER_INTERVAL_SECONDS before next cycle.

    API request budget per cycle:
      1 Explorer request per (game_mode, lobby_type) pair
      + up to EXPLORER_MAX_IDS_PER_QUERY /matches/{id} requests for new IDs only.

    Enabled by USE_EXPLORER=1.
    """
    if not USE_EXPLORER:
        logger.info("[explorer] USE_EXPLORER=0 — loop disabled")
        return

    logger.info(
        "[explorer] starting (interval=%ds, max_ids_per_query=%d, pairs=%s)",
        EXPLORER_INTERVAL_SECONDS, EXPLORER_MAX_IDS_PER_QUERY,
        sorted(ALLOWED_GAME_MODE_PAIRS),
    )

    # Per-pair pointer: only fetch match IDs newer than this on the next cycle.
    # Initialised to None so the first run uses ORDER BY DESC (recent matches).
    _last_match_id: dict[tuple[int, int], int] = {}

    while True:
        cycle_start = time.monotonic()
        try:
            all_rows: list[dict] = []

            for gm, lt in sorted(ALLOWED_GAME_MODE_PAIRS):
                await _rate_limiter.acquire()
                try:
                    rows = await get_explorer_match_rows(
                        game_mode=gm,
                        lobby_type=lt,
                        limit=EXPLORER_MAX_IDS_PER_QUERY,
                        min_match_id=_last_match_id.get((gm, lt)),
                        min_duration=MIN_MATCH_DURATION_SECONDS,
                    )
                    logger.info(
                        "[explorer] SQL (game_mode=%d, lobby_type=%d, min_id=%s) → %d rows",
                        gm, lt, _last_match_id.get((gm, lt)), len(rows),
                    )
                    # Advance the pointer to the highest match_id seen this batch.
                    if rows:
                        new_max = max(r["match_id"] for r in rows)
                        _last_match_id[(gm, lt)] = new_max
                    all_rows.extend(rows)
                except Exception as exc:
                    logger.error(
                        "[explorer] API error (game_mode=%d, lobby_type=%d): %s",
                        gm, lt, exc,
                    )

            logger.info("[explorer] %d total rows to evaluate", len(all_rows))

            saved = 0
            skip_existing = 0
            skip_short = 0
            skip_other = 0

            for row in all_rows:
                match_id = row["match_id"]

                # Skip short matches early — no /matches/{id} call needed.
                duration = row.get("duration")
                if duration is not None and duration < MIN_MATCH_DURATION_SECONDS:
                    logger.debug(
                        "[explorer] match %d: skipped before detail fetch "
                        "(duration=%d < %d)",
                        match_id, duration, MIN_MATCH_DURATION_SECONDS,
                    )
                    skip_short += 1
                    continue

                if match_exists(match_id):
                    skip_existing += 1
                    continue

                ok = await process_single_match(
                    match_id,
                    fallback_avg_rank_tier=row.get("avg_rank_tier"),
                    source="explorer",
                )
                if ok:
                    saved += 1
                else:
                    skip_other += 1

            elapsed = time.monotonic() - cycle_start
            logger.info(
                "[explorer] cycle done (%.1fs): +%d saved | %d existed | "
                "%d short | %d skipped",
                elapsed, saved, skip_existing, skip_short, skip_other,
            )

        except Exception as exc:
            logger.error("[explorer] Unhandled error in cycle: %s", exc, exc_info=True)

        sleep_sec = max(0.0, EXPLORER_INTERVAL_SECONDS - (time.monotonic() - cycle_start))
        logger.info("[explorer] sleeping %.0fs until next cycle...", sleep_sec)
        await asyncio.sleep(sleep_sec)


# ---------------------------------------------------------------------------
# Builds updater — pre-fetches OpenDota data for all heroes into DB cache
# ---------------------------------------------------------------------------

BUILDS_UPDATE_INTERVAL_SECONDS: int = 7 * 86400   # 7 days
BUILDS_SLEEP_BETWEEN_HEROES:    float = 1.5        # seconds between per-hero API calls
OPENDOTA_BASE = "https://api.opendota.com"
DOTACONSTANTS_BASE = "https://raw.githubusercontent.com/odota/dotaconstants/master/build"
CDN_BASE = "https://cdn.cloudflare.steamstatic.com"
VALVE_HERODATA_BASE = "https://www.dota2.com/datafeed"


async def _builds_fetch(url: str) -> dict | list:
    """Simple HTTP GET returning parsed JSON (no rate limiter — used by builds updater only)."""
    import httpx
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


_TALENT_TEMPLATE_RE = re.compile(r'([+\-])?\{s:([^}]+)\}')


def _talent_display_name(talent_key: str, abilities_json: dict) -> str:
    """Converts a talent key (e.g. special_bonus_unique_pudge_3) to a readable name.

    Priority:
      1. dname from abilities.json with no template syntax → return as-is
      2. dname contains {s:KEY} templates → resolve from attrib list
      3. Unresolvable templates or empty dname → clean key-based fallback
    """
    entry = abilities_json.get(talent_key) or {}
    dname = entry.get("dname") or ""
    _fallback = talent_key.removeprefix("special_bonus_").replace("_", " ").title()
    if not dname:
        return _fallback
    if "{" not in dname:
        return dname
    # Build attrib key → value lookup for {s:KEY} substitution
    attrib_map: dict[str, str] = {}
    for _a in (entry.get("attrib") or []):
        if not isinstance(_a, dict) or "key" not in _a:
            continue
        _raw = _a.get("value")
        # dotaconstants sometimes stores values as lists (per-level arrays); take first element
        if isinstance(_raw, list):
            _raw = _raw[0] if _raw else None
        attrib_map[_a["key"]] = str(_raw) if _raw is not None else ""

    def _sub(m: re.Match) -> str:
        sign, key = m.group(1) or "", m.group(2)
        val = attrib_map.get(key)
        if val is None:
            return m.group(0)  # key not in attrib → keep template → triggers fallback below
        return sign + val
    resolved = _TALENT_TEMPLATE_RE.sub(_sub, dname).strip()
    # Fall back if any unresolved templates remain
    if "{" in resolved:
        return _fallback
    return resolved or _fallback


async def _run_builds_update() -> None:
    """Fetches constants + per-hero data, writes to hero_builds_cache / app_cache.

    Flow:
      1. Fetch shared constants: heroes, hero_abilities, items, ability_ids (OpenDota) +
         abilities.json (GitHub dotaconstants for talent dnames).
      2. Save ability_id→name map and items_by_id to app_cache.
      3. For each hero:
         - Facets: Valve API datafeed/herodata (Russian locale → title_loc/description_loc).
         - Talents: OpenDota hero_abilities constants via abilities.json dnames.
         - Start-game items: OpenDota /api/heroes/{id}/itemPopularity.
         - Core items: pre-computed from match_players DB and decoded with items_by_id.
         All saved to hero_builds_cache.
      4. Record builds_last_updated timestamp in app_settings on success.
    """
    logger.info("[builds] Starting builds update run...")

    # ── Shared constants ─────────────────────────────────────────────────
    try:
        heroes_data = await _builds_fetch(f"{OPENDOTA_BASE}/api/constants/heroes")
    except Exception as exc:
        logger.error("[builds] Failed to fetch heroes constants: %s", exc)
        return
    await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)

    try:
        ha_data = await _builds_fetch(f"{OPENDOTA_BASE}/api/constants/hero_abilities")
    except Exception as exc:
        logger.error("[builds] Failed to fetch hero_abilities constants: %s", exc)
        return
    await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)

    try:
        items_data = await _builds_fetch(f"{OPENDOTA_BASE}/api/constants/items")
    except Exception as exc:
        logger.error("[builds] Failed to fetch items constants: %s", exc)
        return
    await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)

    try:
        ability_ids_data = await _builds_fetch(f"{OPENDOTA_BASE}/api/constants/ability_ids")
    except Exception as exc:
        logger.warning("[builds] Failed to fetch ability_ids constants: %s", exc)
        ability_ids_data = {}
    await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)

    try:
        abilities_json = await _builds_fetch(f"{DOTACONSTANTS_BASE}/abilities.json")
    except Exception as exc:
        logger.error("[builds] Failed to fetch abilities.json: %s", exc)
        # Non-fatal: fall back to talent key names
        abilities_json = {}
    await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)

    # ── Diagnostics: verify abilities.json ────────────────────────────────
    _sb_count = sum(1 for k in abilities_json if k.startswith("special_bonus_"))
    _sample   = next((k for k in abilities_json if k.startswith("special_bonus_unique_")), None)
    _sample_dname = (abilities_json.get(_sample) or {}).get("dname") if _sample else None
    logger.info(
        "[builds] abilities.json: total=%d keys, special_bonus_*=%d, sample=%r dname=%r",
        len(abilities_json), _sb_count, _sample, _sample_dname,
    )

    # ── Build and save shared maps ────────────────────────────────────────
    # ability_id → ability_name: primary source is the dedicated ability_ids endpoint
    # which returns { "5003": "antimage_mana_break", ... }
    ability_id_to_name: dict[str, str] = {}
    if isinstance(ability_ids_data, dict):
        for aid_str, aname in ability_ids_data.items():
            if isinstance(aname, str):
                try:
                    ability_id_to_name[str(int(aid_str))] = aname
                except (ValueError, TypeError):
                    pass
    # Fallback: derive from abilities.json id fields (older dotaconstants versions)
    if not ability_id_to_name:
        for aname, ainfo in abilities_json.items():
            if isinstance(ainfo, dict):
                aid = ainfo.get("id")
                if aid is not None:
                    ability_id_to_name[str(int(aid))] = aname
    logger.info("[builds] ability_id_to_name: %d entries (source: %s)",
                len(ability_id_to_name),
                "ability_ids" if isinstance(ability_ids_data, dict) and ability_ids_data else "abilities.json")

    # items_by_id for API endpoint to decode item IDs
    # First pass: collect all component_names referenced in any item's "components" field
    _raw_items = items_data if isinstance(items_data, dict) else {}
    _component_names: set[str] = set()
    for _iinfo in _raw_items.values():
        if isinstance(_iinfo, dict):
            for _cname in (_iinfo.get("components") or []):
                if isinstance(_cname, str):
                    _component_names.add(_cname)
                    _component_names.add("item_" + _cname)

    items_by_id: dict[str, dict] = {}
    items_by_name: dict[str, dict] = {}
    for ikey, iinfo in _raw_items.items():
        if not isinstance(iinfo, dict):
            continue
        iid = iinfo.get("id")
        img = iinfo.get("img") or ""
        if img and not img.startswith("http"):
            img = CDN_BASE + img
        clean = ikey.removeprefix("item_")
        is_component = clean in _component_names or ikey in _component_names
        entry = {
            "id": iid,
            "dname": iinfo.get("dname") or ikey,
            "img": img or None,
            "qual": iinfo.get("qual"),
            "is_component": is_component,
        }
        if iid is not None:
            items_by_id[str(int(iid))] = entry
        items_by_name[ikey]            = entry
        items_by_name[clean]           = entry
        items_by_name["item_" + clean] = entry

    set_app_cache_value("ability_id_to_name", ability_id_to_name)
    set_app_cache_value("items_by_id", items_by_id)
    logger.info(
        "[builds] Saved app_cache: ability_id_to_name=%d entries, items_by_id=%d entries",
        len(ability_id_to_name), len(items_by_id),
    )

    # ── Per-hero data ─────────────────────────────────────────────────────
    if not isinstance(heroes_data, dict):
        logger.error("[builds] heroes_data is not a dict, aborting")
        return

    processed = 0
    failed = 0
    for _key, hero_info in heroes_data.items():
        if not isinstance(hero_info, dict):
            continue
        hero_id  = hero_info.get("id")
        npc_name = hero_info.get("name")
        if not hero_id or not npc_name:
            continue

        hero_ab_data: dict = ha_data.get(npc_name, {}) if isinstance(ha_data, dict) else {}

        # ── Facets + Talents (Valve API, Russian localization) ────────
        await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)
        facets = []
        valve_talent_names: dict[str, str] = {}
        try:
            valve_resp = await _builds_fetch(
                f"{VALVE_HERODATA_BASE}/herodata?hero_id={hero_id}&language=russian"
            )
            _valve_heroes = (
                valve_resp.get("result", {}).get("data", {}).get("heroes") or []
                if isinstance(valve_resp, dict) else []
            )
            _valve_hero = _valve_heroes[0] if _valve_heroes else {}

            # Facets
            for f in (_valve_hero.get("facets") or []):
                if not f.get("title_loc") or not f.get("icon"):
                    continue
                facets.append({
                    "name":        f.get("name"),
                    "icon":        f.get("icon"),
                    "color":       f.get("color"),
                    "gradient_id": f.get("gradient_id"),
                    "title":       f.get("title_loc"),
                    "description": f.get("description_loc") or "",
                })
            logger.info("[builds] hero_id=%s facets from Valve API: %d", hero_id, len(facets))

            # Talents — resolve {s:KEY} templates from special_values
            for t in (_valve_hero.get("talents") or []):
                tname    = t.get("name") or ""
                name_loc = t.get("name_loc") or tname
                sv_map   = {
                    sv["name"]: sv.get("values_float", [None])[0]
                    for sv in (t.get("special_values") or [])
                    if sv.get("name")
                }
                def _sub(m: re.Match) -> str:
                    val = sv_map.get(m.group(1))
                    if val is None:
                        return "?"
                    return str(int(val)) if float(val) == int(val) else str(val)
                valve_talent_names[tname] = re.sub(r"\{s:(\w+)\}", _sub, name_loc)

        except Exception as exc:
            logger.warning("[builds] Valve herodata failed hero_id=%s: %s", hero_id, exc)
            failed += 1

        # ── Talents — build pairs from OpenDota level list ────────────
        TALENT_LEVELS = [10, 15, 20, 25]
        raw_talents = hero_ab_data.get("talents") or []
        talents = []
        for pair_idx, i in enumerate(range(0, len(raw_talents), 2)):
            left_e  = raw_talents[i]     if i     < len(raw_talents) else {}
            right_e = raw_talents[i + 1] if i + 1 < len(raw_talents) else {}
            level   = TALENT_LEVELS[pair_idx] if pair_idx < len(TALENT_LEVELS) else (left_e.get("level") or right_e.get("level"))
            left_key  = left_e.get("name",  "")
            right_key = right_e.get("name", "")
            talents.append({
                "level":         level,
                "left":          valve_talent_names.get(right_key) or _talent_display_name(right_key, abilities_json),
                "left_ability":  right_key,
                "right":         valve_talent_names.get(left_key)  or _talent_display_name(left_key,  abilities_json),
                "right_ability": left_key,
            })

        # ── Start-game items (from OpenDota itemPopularity) ───────────
        await asyncio.sleep(BUILDS_SLEEP_BETWEEN_HEROES)
        try:
            item_pop = await _builds_fetch(
                f"{OPENDOTA_BASE}/api/heroes/{hero_id}/itemPopularity"
            )
        except Exception as exc:
            logger.warning("[builds] itemPopularity failed hero_id=%s: %s", hero_id, exc)
            item_pop = {}
            failed += 1

        start_raw = (item_pop.get("start_game_items") or {}) if isinstance(item_pop, dict) else {}
        start_sorted = sorted(start_raw.items(), key=lambda kv: kv[1], reverse=True)[:6]
        logger.info("[builds] hero_id=%s start_game_items raw top=%s", hero_id,
                    [(k, v) for k, v in start_sorted[:3]])
        start_game_items = []
        for iid_str, _count in start_sorted:
            try:
                info = items_by_id.get(str(int(iid_str)))
            except (ValueError, TypeError):
                logger.debug("[builds] start_game_item bad id: %r", iid_str)
                continue
            if info:
                start_game_items.append({
                    "id":    int(iid_str),
                    "dname": info["dname"],
                    "img":   info["img"],
                })
            else:
                logger.debug("[builds] start_game_item id not in items_by_id: %r", iid_str)

        # ── Core items (from our DB, pre-decoded with items_by_id) ───────
        core_rows = get_hero_core_items(hero_id, top_n=6, min_item_id=50)
        core_items_cached = []
        for _row in core_rows:
            _info = items_by_id.get(str(_row["item_id"])) or {}
            core_items_cached.append({
                "id":      _row["item_id"],
                "dname":   _info.get("dname") or str(_row["item_id"]),
                "img":     _info.get("img"),
                "games":   _row["games"],
                "winrate": _row["winrate"],
            })

        set_hero_build_cache(hero_id, {
            "facets":           facets,
            "talents":          talents,
            "start_game_items": start_game_items,
            "core_items":       core_items_cached,
            "npc_name":         npc_name,
        })
        processed += 1

    # Mark completion
    set_app_setting(
        "builds_last_updated",
        datetime.now(timezone.utc).isoformat(),
    )
    logger.info("[builds] Run complete: %d heroes processed, %d item-pop failures", processed, failed)


async def builds_updater_loop() -> None:
    """Background asyncio task: refreshes hero build cache every 7 days.

    - First run: starts immediately if cache has never been populated
      (no builds_last_updated in app_settings).
    - Subsequent runs: sleeps until 7 days have elapsed since last update.
    - Force trigger: set app_settings.force_builds_update = '1' (e.g. via
      /force_update_builds bot command). Checked every 5 minutes while sleeping.
    """
    logger.info("[builds] builds_updater_loop started (interval=%dd)", BUILDS_UPDATE_INTERVAL_SECONDS // 86400)

    # Env var override: force an immediate rebuild on startup (e.g. after deploys with fixes).
    # Set FORCE_BUILDS_UPDATE_ON_START=1 and restart stats_updater to trigger.
    if os.getenv("FORCE_BUILDS_UPDATE_ON_START", "0") == "1":
        logger.info("[builds] FORCE_BUILDS_UPDATE_ON_START=1 — clearing builds_last_updated")
        set_app_setting("builds_last_updated", "")

    while True:
        last_updated_str = get_app_setting("builds_last_updated")
        force            = get_app_setting("force_builds_update") == "1"

        if force:
            logger.info("[builds] Force update flag detected — starting immediately")
            set_app_setting("force_builds_update", "0")
        elif last_updated_str:
            try:
                last_dt = datetime.fromisoformat(last_updated_str)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_sec = (datetime.now(timezone.utc) - last_dt).total_seconds()
                remaining = BUILDS_UPDATE_INTERVAL_SECONDS - age_sec
            except Exception:
                remaining = 0.0

            if remaining > 0:
                logger.info(
                    "[builds] Cache fresh (last updated %s ago), sleeping %.0fh until next run",
                    last_updated_str, remaining / 3600,
                )
                # Sleep in 5-minute chunks, checking for force flag
                CHECK_INTERVAL = 300.0
                slept = 0.0
                while slept < remaining:
                    await asyncio.sleep(min(CHECK_INTERVAL, remaining - slept))
                    slept += CHECK_INTERVAL
                    if get_app_setting("force_builds_update") == "1":
                        logger.info("[builds] Force flag detected while sleeping")
                        set_app_setting("force_builds_update", "0")
                        break
                else:
                    pass  # normal wake after full interval
                continue  # re-check at top of loop
        else:
            logger.info("[builds] No previous update found — starting initial builds update")

        try:
            await _run_builds_update()
        except Exception as exc:
            logger.error("[builds] Unhandled error in builds update: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Cleanup logic
# ---------------------------------------------------------------------------

async def run_cleanup() -> None:
    """
    Cleanup job (runs every CLEANUP_INTERVAL_HOURS):
      1. Delete matches older than DAYS_TO_KEEP days.
      2. If total count still > MAX_MATCHES, trim the oldest excess.
      3. Full aggregate recalculation if any matches were removed.
    """
    logger.info("[cleanup] Starting cleanup job...")

    # Step 1: delete by age
    old_ids = get_old_match_ids(older_than_days=DAYS_TO_KEEP)
    if old_ids:
        logger.info(
            "[cleanup] Deleting %d matches older than %d days...",
            len(old_ids), DAYS_TO_KEEP,
        )
        delete_matches_and_recalculate(old_ids)
    else:
        logger.info("[cleanup] No matches older than %d days.", DAYS_TO_KEEP)

    # Step 2: cap at MAX_MATCHES
    count_after = get_matches_count()
    if count_after > MAX_MATCHES:
        excess = count_after - MAX_MATCHES
        logger.info(
            "[cleanup] DB has %d matches (limit=%d), trimming %d oldest...",
            count_after, MAX_MATCHES, excess,
        )
        excess_ids = get_oldest_match_ids(excess)
        delete_matches_and_recalculate(excess_ids)
    else:
        logger.info("[cleanup] Match count OK: %d / %d", count_after, MAX_MATCHES)

    logger.info("[cleanup] Cleanup job finished. Current count: %d", get_matches_count())


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("=" * 60)
    logger.info("Stats updater starting")
    logger.info("  [config] Bootstrap mode        = %s", "ON" if STATS_BOOTSTRAP_MODE else "OFF")
    logger.info("  POLL_INTERVAL_MINUTES          = %d", POLL_INTERVAL_MINUTES)
    logger.info("  MAX_MATCHES_PER_CYCLE          = %d", MAX_MATCHES_PER_CYCLE)
    logger.info("  MAX_REQUESTS_PER_MINUTE        = %d", MAX_REQUESTS_PER_MINUTE)
    logger.info("  MAX_MATCHES                    = %d", MAX_MATCHES)
    logger.info("  DAYS_TO_KEEP                   = %d", DAYS_TO_KEEP)
    logger.info("  CLEANUP_INTERVAL_HOURS         = %d", CLEANUP_INTERVAL_HOURS)
    logger.info("  FETCH_MATCH_DETAILS            = %s", FETCH_MATCH_DETAILS)
    logger.info("  USE_EXPLORER                   = %s", USE_EXPLORER)
    logger.info("  EXPLORER_INTERVAL_SECONDS      = %d", EXPLORER_INTERVAL_SECONDS)
    logger.info("  EXPLORER_MAX_IDS_PER_QUERY     = %d", EXPLORER_MAX_IDS_PER_QUERY)
    logger.info("  [config] allowed mode pairs    = %s", sorted(ALLOWED_GAME_MODE_PAIRS))
    logger.info("  [config] rank buckets          = "
                "0→unknown | 1-20→low | 21-35→mid | 36-50→high | 51-60→very_high | 61+→immortal")
    logger.info(
        "  [backfill] ENABLE_BACKFILL_OLD_MATCHES = %s",
        "ON" if ENABLE_BACKFILL_OLD_MATCHES else "OFF (disabled)",
    )
    logger.info("=" * 60)

    # Ensure tables exist (safe to call multiple times)
    init_stats_tables()
    logger.info("[updater] DB tables ready. Current match count: %d", get_matches_count())

    # Start explorer loop as independent background task (runs alongside main loop).
    # It exits immediately if USE_EXPLORER=0 so the task is always safe to create.
    asyncio.create_task(explorer_loop(), name="explorer_loop")

    # Start builds updater — refreshes hero build cache weekly (or on force trigger).
    asyncio.create_task(builds_updater_loop(), name="builds_updater_loop")

    last_cleanup_time: float = 0.0

    while True:
        loop_start = time.monotonic()

        # --- Cleanup job (once per CLEANUP_INTERVAL_HOURS) ---
        if (time.time() - last_cleanup_time) >= CLEANUP_INTERVAL_HOURS * 3600:
            try:
                await run_cleanup()
            except Exception as exc:
                logger.error("[updater] Cleanup job error: %s", exc, exc_info=True)
            last_cleanup_time = time.time()

        # --- Poll for new matches ---
        try:
            await fetch_and_process_matches()
        except Exception as exc:
            logger.error("[updater] Unhandled error in fetch cycle: %s", exc, exc_info=True)

        # --- Backfill match_players for pre-existing matches ---
        # Disabled by default. Set ENABLE_BACKFILL_OLD_MATCHES = True above
        # for a one-off manual run, then set it back to False.
        if ENABLE_BACKFILL_OLD_MATCHES:
            try:
                await backfill_match_player_stats(BACKFILL_MAX_MATCHES_PER_RUN)
            except Exception as exc:
                logger.error("[backfill] Unhandled error: %s", exc, exc_info=True)

        # --- Sleep until next cycle ---
        elapsed = time.monotonic() - loop_start
        sleep_sec = max(0.0, POLL_INTERVAL_MINUTES * 60 - elapsed)
        logger.info(
            "[updater] Sleeping %.0f s until next cycle (cycle took %.1f s)...",
            sleep_sec, elapsed,
        )
        await asyncio.sleep(sleep_sec)


if __name__ == "__main__":
    asyncio.run(main())
