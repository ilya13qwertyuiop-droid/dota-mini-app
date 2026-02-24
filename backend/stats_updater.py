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
# Match parsing helpers
# ---------------------------------------------------------------------------

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
    return {
        "match_id": match_id,
        "start_time": match.get("start_time") or 0,
        "duration": match.get("duration"),
        "patch": str(patch_val) if patch_val is not None else None,
        "avg_rank_tier": match.get("avg_rank_tier"),
        "radiant_win": bool(match.get("radiant_win", False)),
        "radiant_heroes": radiant_heroes,
        "dire_heroes": dire_heroes,
    }


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

        parsed = _parse_match_details(details)
        if parsed is None:
            skip_incomplete += 1
            continue

        try:
            save_match_and_update_aggregates(**parsed)
            new_count += 1
        except Exception as exc:
            logger.error("[updater] Failed to save match %d: %s", match_id, exc)

    logger.info(
        "[updater] Cycle done: +%d new | %d already existed | %d incomplete",
        new_count, skip_existing, skip_incomplete,
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
    logger.info("  POLL_INTERVAL_MINUTES   = %d", POLL_INTERVAL_MINUTES)
    logger.info("  MAX_REQUESTS_PER_MINUTE = %d", MAX_REQUESTS_PER_MINUTE)
    logger.info("  MAX_MATCHES             = %d", MAX_MATCHES)
    logger.info("  DAYS_TO_KEEP            = %d", DAYS_TO_KEEP)
    logger.info("  CLEANUP_INTERVAL_HOURS  = %d", CLEANUP_INTERVAL_HOURS)
    logger.info("  MAX_MATCHES_PER_CYCLE   = %d", MAX_MATCHES_PER_CYCLE)
    logger.info("  FETCH_MATCH_DETAILS     = %s", FETCH_MATCH_DETAILS)
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
