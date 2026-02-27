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
    STATS_BOOTSTRAP_MODE      — set to "1" or "true" to enable aggressive settings
                                 for rapid initial DB population (default: "0").
                                 Overrides POLL_INTERVAL_MINUTES → 5,
                                 MAX_MATCHES_PER_CYCLE → 100,
                                 MAX_REQUESTS_PER_MINUTE → 200.
                                 Peak API rate: ~200 req/min during the burst window
                                 (~30 s), then idle — well under the 3000 req/min limit.

Game-mode filter (hardcoded, see ALLOWED_GAME_MODES below):
    Only All Pick (game_mode=1) and Ranked All Pick (game_mode=22) are saved.
    All other modes (Turbo=23, Ability Draft=18, etc.) are silently skipped.

Backfill of legacy matches:
    ENABLE_BACKFILL_OLD_MATCHES is hardcoded to False.
    The backfill functions are preserved in this file but not called.
    To run a one-off legacy backfill, set the flag to True and restart.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
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

from backend.opendota_client import get_public_matches, get_match_details
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
# Game-mode allow-list
# ---------------------------------------------------------------------------

# OpenDota game_mode values for the modes we want to ingest.
#   1  = All Pick (unranked public)
#   22 = Ranked All Pick
# Everything else (Turbo=23, Ability Draft=18, CM=2, bots, etc.) is dropped.
ALLOWED_GAME_MODES: frozenset[int] = frozenset({1, 22})

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

    Picks up to 3 "core" items from slots item_0..item_5 by filtering out
    cheap consumables defined in _JUNK_ITEM_IDS.  Missing or 0-valued slots
    are also skipped.  The result is padded with None up to 3 entries.
    """
    raw_items = [player.get(f"item_{i}", 0) or 0 for i in range(6)]
    core_items: list[int | None] = [
        iid for iid in raw_items if iid and iid not in _JUNK_ITEM_IDS
    ][:3]
    while len(core_items) < 3:
        core_items.append(None)

    slot = player.get("player_slot", 128)
    return {
        "hero_id":      player.get("hero_id"),
        "player_slot":  slot,
        "is_radiant":   1 if slot < 128 else 0,
        "lane":         player.get("lane"),
        "lane_role":    player.get("lane_role"),
        "gpm":          player.get("gold_per_min"),
        "xpm":          player.get("xp_per_min"),
        "kills":        player.get("kills"),
        "deaths":       player.get("deaths"),
        "assists":      player.get("assists"),
        "hero_damage":  player.get("hero_damage"),
        "tower_damage": player.get("tower_damage"),
        "obs_placed":   player.get("obs_placed"),
        "sen_placed":   player.get("sen_placed"),
        "item0":        core_items[0],
        "item1":        core_items[1],
        "item2":        core_items[2],
    }


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
    }


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
    One polling cycle:
      1. Fetch recent public match IDs from /publicMatches (1 request).
      2. If FETCH_MATCH_DETAILS is disabled: log a warning and return — hero data
         is not available from publicMatches alone.
      3. If FETCH_MATCH_DETAILS is enabled: for each new match_id, call
         /matches/{id} (rate-limited) to get hero and result data, then save.
    """
    await _rate_limiter.acquire()
    try:
        raw_matches = await get_public_matches()
    except Exception as exc:
        logger.error("[updater] Failed to fetch public matches: %s", exc)
        return

    logger.info("[updater] publicMatches returned %d entries", len(raw_matches))

    if not FETCH_MATCH_DETAILS:
        logger.warning(
            "[updater] FETCH_MATCH_DETAILS is disabled. "
            "publicMatches does not provide hero data "
            "(radiant_team/dire_team fields are zeroed by the API). "
            "Set FETCH_MATCH_DETAILS=1 to enable hero statistics collection."
        )
        return

    new_count = 0
    skip_existing = 0
    skip_incomplete = 0
    skip_game_mode = 0
    # Diagnostic flag: log raw details only for the first non-skipped match per cycle.
    _details_diag_done = False
    # Fallback diag: log avg_rank_tier substitution only once per cycle.
    _fallback_diag_done = False

    for raw in raw_matches[:MAX_MATCHES_PER_CYCLE]:
        basic = _parse_public_match(raw)
        if basic is None:
            continue

        match_id = basic["match_id"]

        if match_exists(match_id):
            skip_existing += 1
            continue

        # Hero data is only available via the full match details endpoint
        await _rate_limiter.acquire()
        try:
            details = await get_match_details(match_id)
        except Exception as exc:
            logger.warning(
                "[updater] HTTP error fetching details for match %d: %s", match_id, exc
            )
            continue

        # Diagnostic point 1: compare avg_rank_tier from publicMatches vs /matches/{id}.
        # Fires once per cycle (first non-existing match fetched).
        # This reveals whether the details endpoint actually returns avg_rank_tier.
        if not _details_diag_done:
            _details_diag_done = True
            logger.info(
                "[diag] raw OpenDota match %s: avg_rank_tier=%r  keys=%s",
                match_id,
                details.get("avg_rank_tier"),
                sorted(details.keys()),
            )
            logger.info(
                "[diag] avg_rank_tier source compare: publicMatches=%r  /matches/{id}=%r",
                basic.get("avg_rank_tier"),
                details.get("avg_rank_tier"),
            )

        parsed = _parse_match_details(details)
        if parsed is None:
            skip_incomplete += 1
            continue

        # --- Game-mode filter: only All Pick (1) and Ranked All Pick (22) ---
        game_mode = parsed.get("game_mode")
        if game_mode not in ALLOWED_GAME_MODES:
            logger.debug(
                "[updater] match %d: skipped (game_mode=%s not in allowed set %s)",
                match_id, game_mode, ALLOWED_GAME_MODES,
            )
            skip_game_mode += 1
            continue

        # Fallback: /matches/{id} often omits avg_rank_tier; use publicMatches value.
        if parsed["avg_rank_tier"] is None:
            fallback = basic.get("avg_rank_tier")
            if fallback is not None:
                parsed["avg_rank_tier"] = fallback
                parsed["rank_bucket"] = _rank_bucket_for_tier(fallback)
                if not _fallback_diag_done:
                    _fallback_diag_done = True
                    logger.info(
                        "[diag] applied avg_rank_tier fallback for match %s: "
                        "publicMatches=%r → bucket=%s",
                        match_id, fallback, parsed["rank_bucket"],
                    )

        try:
            logger.info(
                "[diag] saving match %s with game_mode=%s, lobby_type=%s",
                parsed.get("match_id"), parsed.get("game_mode"), parsed.get("lobby_type"),
            )
            save_match_and_update_aggregates(**parsed)
            new_count += 1
            if new_count == 1:
                logger.info(
                    "[updater] rank example: match=%d avg_rank_tier=%s → bucket=%s",
                    parsed["match_id"], parsed.get("avg_rank_tier"), parsed.get("rank_bucket"),
                )
        except Exception as exc:
            logger.error("[updater] Failed to save match %d: %s", match_id, exc)

    logger.info(
        "[updater] Cycle done: +%d new | %d existed | %d incomplete | %d wrong game_mode",
        new_count, skip_existing, skip_incomplete, skip_game_mode,
    )


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
