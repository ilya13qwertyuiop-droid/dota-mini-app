"""
stats_db.py — Database layer for the custom Dota 2 statistics collection.

Tables (all in the same DB, configured via DATABASE_URL):
  matches        — raw match records
  hero_matchups  — hero A vs hero B (opponents), aggregated
  hero_synergy   — hero A with hero B (same team), aggregated
  hero_stats     — per-hero total games/wins across all matches

Previously used raw sqlite3.connect(). Now uses SQLAlchemy Core (engine from
database.py) so it works with both SQLite and PostgreSQL unchanged.

Key SQLite→Postgres portability notes:
  - INSERT OR IGNORE → INSERT ... ON CONFLICT (match_id) DO NOTHING
    (supported in both PG 9.5+ and SQLite 3.24+)
  - INSERT ... ON CONFLICT (...) DO UPDATE SET ... excluded.*
    (identical syntax in both PG 9.5+ and SQLite 3.24+)
  - ? placeholders → :name bindparams (SQLAlchemy text() handles the mapping)
  - PRAGMA journal_mode/synchronous → moved to database.py engine event
  - BEGIN IMMEDIATE → dropped; engine.begin() is sufficient for single-writer
  - executescript() → individual conn.execute(text(...)) calls
  - sqlite3.Row row_factory → result.mappings().all()

Key convention for matchup/synergy pairs:
  hero_a < hero_b  (canonical order, no duplicates)
  In hero_matchups, `wins` = wins by hero_a (the one with the smaller ID).
"""

import json
import logging
import time
from typing import Optional

from sqlalchemy import text

from backend.config import ALLOWED_GAME_MODE_PAIRS, MIN_MATCH_DURATION_SECONDS
from backend.database import engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema init (idempotent; kept for backward compat with stats_updater.py)
# ---------------------------------------------------------------------------

def init_stats_tables() -> None:
    """Creates all stats tables if they don't exist yet.

    For PostgreSQL in production use Alembic instead.
    The CREATE TABLE IF NOT EXISTS DDL below is valid in both SQLite and PG.
    """
    from backend.database import create_all_tables
    create_all_tables()  # imports all models internally and runs CREATE TABLE IF NOT EXISTS

    # ------------------------------------------------------------------ #
    # Idempotent column migrations (ALTER TABLE … ADD COLUMN …).          #
    # Each ALTER is attempted inside its own transaction; the except block #
    # silently ignores "column already exists" / "duplicate column" errors #
    # so the function is safe to call multiple times.                      #
    # ------------------------------------------------------------------ #

    # Migration 1: add rank_bucket to matches (pre-dates 0001 migration)
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE matches ADD COLUMN rank_bucket VARCHAR(16)"))
        logger.info("[stats_db] Migration applied: added rank_bucket to matches")
    except Exception:
        pass  # column already exists

    # Migration 2: add extended per-player columns to match_players.
    # Needed when the table was created before this migration (e.g. from an
    # older code version that only had the four basic columns).
    _mp_new_columns = [
        ("lane",         "ALTER TABLE match_players ADD COLUMN lane SMALLINT"),
        ("lane_role",    "ALTER TABLE match_players ADD COLUMN lane_role SMALLINT"),
        ("gpm",          "ALTER TABLE match_players ADD COLUMN gpm INTEGER"),
        ("xpm",          "ALTER TABLE match_players ADD COLUMN xpm INTEGER"),
        ("kills",        "ALTER TABLE match_players ADD COLUMN kills INTEGER"),
        ("deaths",       "ALTER TABLE match_players ADD COLUMN deaths INTEGER"),
        ("assists",      "ALTER TABLE match_players ADD COLUMN assists INTEGER"),
        ("hero_damage",  "ALTER TABLE match_players ADD COLUMN hero_damage INTEGER"),
        ("tower_damage", "ALTER TABLE match_players ADD COLUMN tower_damage INTEGER"),
        ("obs_placed",   "ALTER TABLE match_players ADD COLUMN obs_placed INTEGER"),
        ("sen_placed",   "ALTER TABLE match_players ADD COLUMN sen_placed INTEGER"),
        ("item0",        "ALTER TABLE match_players ADD COLUMN item0 INTEGER"),
        ("item1",        "ALTER TABLE match_players ADD COLUMN item1 INTEGER"),
        ("item2",        "ALTER TABLE match_players ADD COLUMN item2 INTEGER"),
    ]
    applied: list[str] = []
    for col_name, ddl in _mp_new_columns:
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
            applied.append(col_name)
        except Exception:
            pass  # column already exists
    if applied:
        logger.info(
            "[stats_db] Migration applied: added to match_players: %s",
            ", ".join(applied),
        )

    # Migration 3: add extended per-player stats columns (second batch).
    _mp_new_columns_v2 = [
        ("last_hits",    "ALTER TABLE match_players ADD COLUMN last_hits INTEGER"),
        ("denies",       "ALTER TABLE match_players ADD COLUMN denies INTEGER"),
        ("hero_healing", "ALTER TABLE match_players ADD COLUMN hero_healing INTEGER"),
        ("net_worth",    "ALTER TABLE match_players ADD COLUMN net_worth INTEGER"),
        ("item3",        "ALTER TABLE match_players ADD COLUMN item3 INTEGER"),
        ("item4",        "ALTER TABLE match_players ADD COLUMN item4 INTEGER"),
        ("item5",        "ALTER TABLE match_players ADD COLUMN item5 INTEGER"),
    ]
    applied_v2: list[str] = []
    for col_name, ddl in _mp_new_columns_v2:
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
            applied_v2.append(col_name)
        except Exception:
            pass  # column already exists
    if applied_v2:
        logger.info(
            "[stats_db] Migration applied: added to match_players: %s",
            ", ".join(applied_v2),
        )

    # Migration 4: add game_mode to matches.
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE matches ADD COLUMN game_mode SMALLINT"))
        logger.info("[stats_db] Migration applied: added game_mode to matches")
    except Exception:
        pass  # column already exists

    # Migration 5: add lobby_type to matches.
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE matches ADD COLUMN lobby_type SMALLINT"))
        logger.info("[stats_db] Migration applied: added lobby_type to matches")
    except Exception:
        pass  # column already exists

    logger.info("[stats_db] Tables ready (matches, match_players, hero_matchups, hero_synergy, hero_stats)")


# ---------------------------------------------------------------------------
# Idempotent match ingestion
# ---------------------------------------------------------------------------

def match_exists(match_id: int) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM matches WHERE match_id = :id"),
            {"id": match_id},
        )
        return result.fetchone() is not None


def save_match_and_update_aggregates(
    match_id: int,
    start_time: int,
    duration: Optional[int],
    patch: Optional[str],
    avg_rank_tier: Optional[int],
    rank_bucket: Optional[str],
    radiant_win: bool,
    radiant_heroes: list[int],
    dire_heroes: list[int],
    game_mode: Optional[int] = None,
    lobby_type: Optional[int] = None,
    players: Optional[list[dict]] = None,
) -> None:
    """Atomically saves one match and updates all aggregate tables.

    Idempotent: uses INSERT ... ON CONFLICT (match_id) DO NOTHING and skips
    aggregate updates when the row already existed (rowcount == 0).
    This syntax is identical in PostgreSQL 9.5+ and SQLite 3.24+.

    game_mode — OpenDota game_mode code (1=All Pick, 22=Ranked All Pick).
      The caller (fetch_and_process_matches) has already filtered out
      disallowed modes; this value is stored as-is for reference.

    lobby_type — OpenDota lobby_type code (0=public, 7=ranked, etc.).
      Stored as-is for diagnostic purposes.

    players — optional list of per-player dicts (from _parse_match_details).
      Each dict must contain: hero_id, player_slot, is_radiant and any subset
      of the extended stats fields.  Rows are inserted with ON CONFLICT DO
      NOTHING so re-running on an already-saved match is safe.
    """
    # --- Hard gate: never write a match with missing or disallowed game_mode/lobby_type ---
    # This is the last line of defence: even if a caller skips its own filter
    # (e.g. an old worker process that hasn't been restarted after a deploy),
    # nothing leaks into the DB.
    if game_mode is None or lobby_type is None or (game_mode, lobby_type) not in ALLOWED_GAME_MODE_PAIRS:
        logger.error(
            "[stats_db] BLOCKED write: match %s has game_mode=%s, lobby_type=%s "
            "— not in ALLOWED_GAME_MODE_PAIRS %s. Match will NOT be saved.",
            match_id, game_mode, lobby_type, ALLOWED_GAME_MODE_PAIRS,
        )
        return

    logger.info(
        "[diag] inserting/updating match %s with game_mode=%s, lobby_type=%s",
        match_id, game_mode, lobby_type,
    )
    with engine.begin() as conn:
        # ----- Insert match (idempotent) -----
        result = conn.execute(
            text("""
                INSERT INTO matches
                    (match_id, start_time, duration, patch, avg_rank_tier, rank_bucket,
                     game_mode, lobby_type, radiant_win, radiant_heroes, dire_heroes)
                VALUES
                    (:match_id, :start_time, :duration, :patch, :avg_rank_tier, :rank_bucket,
                     :game_mode, :lobby_type, :radiant_win, :radiant_heroes, :dire_heroes)
                ON CONFLICT (match_id) DO NOTHING
            """),
            {
                "match_id": match_id,
                "start_time": start_time,
                "duration": duration,
                "patch": patch,
                "avg_rank_tier": avg_rank_tier,
                "rank_bucket": rank_bucket,
                "game_mode": game_mode,
                "lobby_type": lobby_type,
                "radiant_win": int(radiant_win),
                "radiant_heroes": json.dumps(radiant_heroes),
                "dire_heroes": json.dumps(dire_heroes),
            },
        )

        is_new = result.rowcount == 1

        logger.info(
            "[diag] matches upsert done for %s: game_mode=%s, lobby_type=%s  (new_row=%s)",
            match_id, game_mode, lobby_type, is_new,
        )

        if not is_new:
            # Match already in DB — skip aggregate updates to keep counts correct
            return

        # ----- Duration filter -----
        # Matches shorter than MIN_MATCH_DURATION_SECONDS (15 min) are stored
        # in the matches table but excluded from all derivative tables
        # (match_players, hero_stats, hero_matchups, hero_synergy).
        # duration=None means the API didn't return it — treated as passing.
        if duration is not None and duration < MIN_MATCH_DURATION_SECONDS:
            logger.debug(
                "[stats_db] match %s: duration=%ds < %ds — "
                "skipped from hero_stats / hero_matchups / hero_synergy",
                match_id, duration, MIN_MATCH_DURATION_SECONDS,
            )
            return

        # ----- Insert per-player records (if provided) -----
        if players:
            for p in players:
                conn.execute(
                    text("""
                        INSERT INTO match_players
                            (match_id, hero_id, player_slot, is_radiant,
                             lane, lane_role, gpm, xpm,
                             kills, deaths, assists,
                             hero_damage, tower_damage,
                             obs_placed, sen_placed,
                             item0, item1, item2,
                             last_hits, denies, hero_healing, net_worth,
                             item3, item4, item5)
                        VALUES
                            (:match_id, :hero_id, :player_slot, :is_radiant,
                             :lane, :lane_role, :gpm, :xpm,
                             :kills, :deaths, :assists,
                             :hero_damage, :tower_damage,
                             :obs_placed, :sen_placed,
                             :item0, :item1, :item2,
                             :last_hits, :denies, :hero_healing, :net_worth,
                             :item3, :item4, :item5)
                        ON CONFLICT (match_id, player_slot) DO NOTHING
                    """),
                    {**p, "match_id": match_id},
                )

        # ----- hero_stats -----
        for h in radiant_heroes:
            conn.execute(
                text("""
                    INSERT INTO hero_stats (hero_id, games, wins) VALUES (:h, 1, :w)
                    ON CONFLICT (hero_id) DO UPDATE SET
                        games = hero_stats.games + 1,
                        wins  = hero_stats.wins  + excluded.wins
                """),
                {"h": h, "w": int(radiant_win)},
            )
        for h in dire_heroes:
            conn.execute(
                text("""
                    INSERT INTO hero_stats (hero_id, games, wins) VALUES (:h, 1, :w)
                    ON CONFLICT (hero_id) DO UPDATE SET
                        games = hero_stats.games + 1,
                        wins  = hero_stats.wins  + excluded.wins
                """),
                {"h": h, "w": int(not radiant_win)},
            )

        # ----- hero_matchups -----
        for r_hero in radiant_heroes:
            for d_hero in dire_heroes:
                if r_hero == d_hero:
                    continue
                a = min(r_hero, d_hero)
                b = max(r_hero, d_hero)
                a_wins = int((r_hero < d_hero) == radiant_win)
                conn.execute(
                    text("""
                        INSERT INTO hero_matchups (hero_a, hero_b, games, wins)
                        VALUES (:a, :b, 1, :w)
                        ON CONFLICT (hero_a, hero_b) DO UPDATE SET
                            games = hero_matchups.games + 1,
                            wins  = hero_matchups.wins  + excluded.wins
                    """),
                    {"a": a, "b": b, "w": a_wins},
                )

        # ----- hero_synergy -----
        for heroes, team_won in [
            (radiant_heroes, radiant_win),
            (dire_heroes, not radiant_win),
        ]:
            n = len(heroes)
            for i in range(n):
                for j in range(i + 1, n):
                    a = min(heroes[i], heroes[j])
                    b = max(heroes[i], heroes[j])
                    conn.execute(
                        text("""
                            INSERT INTO hero_synergy (hero_a, hero_b, games, wins)
                            VALUES (:a, :b, 1, :w)
                            ON CONFLICT (hero_a, hero_b) DO UPDATE SET
                                games = hero_synergy.games + 1,
                                wins  = hero_synergy.wins  + excluded.wins
                        """),
                        {"a": a, "b": b, "w": int(team_won)},
                    )
        # engine.begin() auto-commits here


# ---------------------------------------------------------------------------
# Reads for the API endpoints
# ---------------------------------------------------------------------------

def get_hero_matchup_rows(hero_id: int, min_games: int = 50) -> list[dict]:
    """Returns all opponent matchup rows for a hero (with win rate from hero's perspective)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT hero_a, hero_b, games, wins FROM hero_matchups"
                " WHERE (hero_a = :id OR hero_b = :id) AND games >= :min"
            ),
            {"id": hero_id, "min": min_games},
        ).mappings().all()

    result = []
    for row in rows:
        hero_a, hero_b, games, wins = row["hero_a"], row["hero_b"], row["games"], row["wins"]
        if hero_a == hero_id:
            opponent_id = hero_b
            hero_wins = wins
        else:
            opponent_id = hero_a
            hero_wins = games - wins
        result.append(
            {
                "hero_id": opponent_id,
                "games": games,
                "wins": hero_wins,
                "wr_vs": round(hero_wins / games, 4) if games > 0 else 0.0,
            }
        )
    return result


def get_hero_base_winrate_from_db(hero_id: int) -> Optional[float]:
    """Returns hero's overall winrate from hero_stats (computed from our match data)."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT games, wins FROM hero_stats WHERE hero_id = :id"),
            {"id": hero_id},
        ).mappings().fetchone()

    if not row or row["games"] == 0:
        return None
    return round(row["wins"] / row["games"], 4)


def get_hero_total_games(hero_id: int) -> int:
    """Returns total number of games for a hero from hero_stats."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT games FROM hero_stats WHERE hero_id = :id"),
            {"id": hero_id},
        ).mappings().fetchone()
    return row["games"] if row else 0


def get_hero_synergy_rows(hero_id: int, min_games: int = 50) -> list[dict]:
    """Returns all ally synergy rows for a hero."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT hero_a, hero_b, games, wins FROM hero_synergy"
                " WHERE (hero_a = :id OR hero_b = :id) AND games >= :min"
            ),
            {"id": hero_id, "min": min_games},
        ).mappings().all()

    result = []
    for row in rows:
        hero_a, hero_b, games, wins = row["hero_a"], row["hero_b"], row["games"], row["wins"]
        ally_id = hero_b if hero_a == hero_id else hero_a
        result.append(
            {
                "hero_id": ally_id,
                "games": games,
                "wins": wins,
                "wr_vs": round(wins / games, 4) if games > 0 else 0.0,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Cleanup & maintenance
# ---------------------------------------------------------------------------

def get_matches_count() -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM matches")).scalar() or 0


def get_old_match_ids(older_than_days: int) -> list[int]:
    """Returns match_ids with start_time older than `older_than_days` days."""
    cutoff = int(time.time()) - older_than_days * 86400
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT match_id FROM matches"
                " WHERE start_time < :cutoff ORDER BY start_time ASC"
            ),
            {"cutoff": cutoff},
        ).fetchall()
    return [r[0] for r in rows]


def get_oldest_match_ids(count: int) -> list[int]:
    """Returns the `count` oldest match_ids (for max-cap enforcement)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT match_id FROM matches ORDER BY start_time ASC LIMIT :n"),
            {"n": count},
        ).fetchall()
    return [r[0] for r in rows]


def delete_matches_and_recalculate(match_ids: list[int]) -> None:
    """Deletes the specified matches then fully recalculates all aggregates.

    Recalculation: accumulate in Python dicts → bulk INSERT (faster than
    per-row upserts when many rows are deleted at once).
    """
    if not match_ids:
        return

    with engine.begin() as conn:
        # Delete player records first (explicit, not relying on FK cascade so
        # this works on SQLite regardless of PRAGMA foreign_keys setting).
        conn.execute(
            text("DELETE FROM match_players WHERE match_id = :id"),
            [{"id": mid} for mid in match_ids],
        )
        # Delete the unwanted matches
        conn.execute(
            text("DELETE FROM matches WHERE match_id = :id"),
            [{"id": mid} for mid in match_ids],
        )

        # Wipe all aggregates
        conn.execute(text("DELETE FROM hero_matchups"))
        conn.execute(text("DELETE FROM hero_synergy"))
        conn.execute(text("DELETE FROM hero_stats"))

        # Load all remaining matches; apply the same duration filter used at
        # ingest time so rebuilt aggregates are consistent with live ingestion.
        remaining = conn.execute(
            text(
                "SELECT radiant_win, radiant_heroes, dire_heroes FROM matches"
                " WHERE duration IS NULL OR duration >= :min_dur"
            ),
            {"min_dur": MIN_MATCH_DURATION_SECONDS},
        ).mappings().all()

        # Accumulate in Python dicts (much faster than per-row upserts)
        matchups: dict[tuple[int, int], list[int]] = {}
        synergy: dict[tuple[int, int], list[int]] = {}
        stats: dict[int, list[int]] = {}

        for row in remaining:
            radiant_win = bool(row["radiant_win"])
            r_heroes: list[int] = json.loads(row["radiant_heroes"])
            d_heroes: list[int] = json.loads(row["dire_heroes"])

            for h in r_heroes:
                if h not in stats:
                    stats[h] = [0, 0]
                stats[h][0] += 1
                stats[h][1] += int(radiant_win)
            for h in d_heroes:
                if h not in stats:
                    stats[h] = [0, 0]
                stats[h][0] += 1
                stats[h][1] += int(not radiant_win)

            for r in r_heroes:
                for d in d_heroes:
                    if r == d:
                        continue
                    a, b = min(r, d), max(r, d)
                    a_wins = int((r < d) == radiant_win)
                    key = (a, b)
                    if key not in matchups:
                        matchups[key] = [0, 0]
                    matchups[key][0] += 1
                    matchups[key][1] += a_wins

            for heroes, won in [
                (r_heroes, radiant_win),
                (d_heroes, not radiant_win),
            ]:
                n = len(heroes)
                for i in range(n):
                    for j in range(i + 1, n):
                        a, b = min(heroes[i], heroes[j]), max(heroes[i], heroes[j])
                        key = (a, b)
                        if key not in synergy:
                            synergy[key] = [0, 0]
                        synergy[key][0] += 1
                        synergy[key][1] += int(won)

        # Bulk insert recalculated aggregates
        if matchups:
            conn.execute(
                text(
                    "INSERT INTO hero_matchups (hero_a, hero_b, games, wins)"
                    " VALUES (:a, :b, :g, :w)"
                ),
                [{"a": a, "b": b, "g": v[0], "w": v[1]} for (a, b), v in matchups.items()],
            )
        if synergy:
            conn.execute(
                text(
                    "INSERT INTO hero_synergy (hero_a, hero_b, games, wins)"
                    " VALUES (:a, :b, :g, :w)"
                ),
                [{"a": a, "b": b, "g": v[0], "w": v[1]} for (a, b), v in synergy.items()],
            )
        if stats:
            conn.execute(
                text(
                    "INSERT INTO hero_stats (hero_id, games, wins) VALUES (:h, :g, :w)"
                ),
                [{"h": h, "g": v[0], "w": v[1]} for h, v in stats.items()],
            )
        # engine.begin() auto-commits here

    logger.info(
        "[stats_db] Cleanup done: deleted %d matches, remaining=%d,"
        " matchup_pairs=%d, synergy_pairs=%d",
        len(match_ids),
        len(remaining),
        len(matchups),
        len(synergy),
    )


# ---------------------------------------------------------------------------
# Stand-alone aggregate rebuild (admin / one-off use)
# ---------------------------------------------------------------------------

def recalculate_all_aggregates() -> None:
    """Wipes hero_stats, hero_matchups, hero_synergy and rebuilds from scratch.

    No matches are deleted.  The same duration filter that guards ingestion
    (MIN_MATCH_DURATION_SECONDS) is applied here, so the resulting aggregates
    are consistent with what future ingestion would produce.

    Typical use: run after changing MIN_MATCH_DURATION_SECONDS or after a
    bulk import / data-quality fix.  See backend/admin_recalc.py.
    """
    logger.info(
        "[stats_db] recalculate_all_aggregates: starting"
        " (min_duration=%ds)", MIN_MATCH_DURATION_SECONDS,
    )

    with engine.begin() as conn:
        # Wipe all aggregates atomically together with the rebuild
        conn.execute(text("DELETE FROM hero_matchups"))
        conn.execute(text("DELETE FROM hero_synergy"))
        conn.execute(text("DELETE FROM hero_stats"))

        remaining = conn.execute(
            text(
                "SELECT radiant_win, radiant_heroes, dire_heroes FROM matches"
                " WHERE duration IS NULL OR duration >= :min_dur"
            ),
            {"min_dur": MIN_MATCH_DURATION_SECONDS},
        ).mappings().all()

        matchups: dict[tuple[int, int], list[int]] = {}
        synergy: dict[tuple[int, int], list[int]] = {}
        stats: dict[int, list[int]] = {}

        for row in remaining:
            radiant_win = bool(row["radiant_win"])
            r_heroes: list[int] = json.loads(row["radiant_heroes"])
            d_heroes: list[int] = json.loads(row["dire_heroes"])

            for h in r_heroes:
                if h not in stats:
                    stats[h] = [0, 0]
                stats[h][0] += 1
                stats[h][1] += int(radiant_win)
            for h in d_heroes:
                if h not in stats:
                    stats[h] = [0, 0]
                stats[h][0] += 1
                stats[h][1] += int(not radiant_win)

            for r in r_heroes:
                for d in d_heroes:
                    if r == d:
                        continue
                    a, b = min(r, d), max(r, d)
                    a_wins = int((r < d) == radiant_win)
                    key = (a, b)
                    if key not in matchups:
                        matchups[key] = [0, 0]
                    matchups[key][0] += 1
                    matchups[key][1] += a_wins

            for heroes, won in [
                (r_heroes, radiant_win),
                (d_heroes, not radiant_win),
            ]:
                n = len(heroes)
                for i in range(n):
                    for j in range(i + 1, n):
                        a, b = min(heroes[i], heroes[j]), max(heroes[i], heroes[j])
                        key = (a, b)
                        if key not in synergy:
                            synergy[key] = [0, 0]
                        synergy[key][0] += 1
                        synergy[key][1] += int(won)

        if matchups:
            conn.execute(
                text("INSERT INTO hero_matchups (hero_a, hero_b, games, wins)"
                     " VALUES (:a, :b, :g, :w)"),
                [{"a": a, "b": b, "g": v[0], "w": v[1]} for (a, b), v in matchups.items()],
            )
        if synergy:
            conn.execute(
                text("INSERT INTO hero_synergy (hero_a, hero_b, games, wins)"
                     " VALUES (:a, :b, :g, :w)"),
                [{"a": a, "b": b, "g": v[0], "w": v[1]} for (a, b), v in synergy.items()],
            )
        if stats:
            conn.execute(
                text("INSERT INTO hero_stats (hero_id, games, wins) VALUES (:h, :g, :w)"),
                [{"h": h, "g": v[0], "w": v[1]} for h, v in stats.items()],
            )
        # engine.begin() auto-commits here

    logger.info(
        "[stats_db] recalculate_all_aggregates: done"
        " — matches_used=%d, matchup_pairs=%d, synergy_pairs=%d, heroes=%d",
        len(remaining), len(matchups), len(synergy), len(stats),
    )


# ---------------------------------------------------------------------------
# Backfill helpers — match_players for pre-existing matches
# ---------------------------------------------------------------------------

def get_match_ids_needing_backfill(limit: int) -> list[int]:
    """Returns up to `limit` match_ids that have no rows in match_players yet.

    These are matches saved before the match_players table existed (or before
    the current code version).  Ordered by match_id ascending so progress is
    monotonically forward.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT m.match_id FROM matches m
                WHERE NOT EXISTS (
                    SELECT 1 FROM match_players mp WHERE mp.match_id = m.match_id
                )
                ORDER BY m.match_id
                LIMIT :lim
            """),
            {"lim": limit},
        ).fetchall()
    return [r[0] for r in rows]


def count_matches_needing_backfill() -> int:
    """Returns count of matches that have no match_players rows."""
    with engine.connect() as conn:
        return conn.execute(
            text("""
                SELECT COUNT(*) FROM matches m
                WHERE NOT EXISTS (
                    SELECT 1 FROM match_players mp WHERE mp.match_id = m.match_id
                )
            """)
        ).scalar() or 0


def update_match_players_backfill(match_id: int, players: list[dict]) -> None:
    """Replaces match_players rows for a single match (backfill path).

    Deletes any existing (possibly partial) rows then inserts fresh ones so
    the operation is idempotent even if the backfill worker is restarted.
    """
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM match_players WHERE match_id = :mid"),
            {"mid": match_id},
        )
        for p in players:
            conn.execute(
                text("""
                    INSERT INTO match_players
                        (match_id, hero_id, player_slot, is_radiant,
                         lane, lane_role, gpm, xpm,
                         kills, deaths, assists,
                         hero_damage, tower_damage,
                         obs_placed, sen_placed,
                         item0, item1, item2,
                         last_hits, denies, hero_healing, net_worth,
                         item3, item4, item5)
                    VALUES
                        (:match_id, :hero_id, :player_slot, :is_radiant,
                         :lane, :lane_role, :gpm, :xpm,
                         :kills, :deaths, :assists,
                         :hero_damage, :tower_damage,
                         :obs_placed, :sen_placed,
                         :item0, :item1, :item2,
                         :last_hits, :denies, :hero_healing, :net_worth,
                         :item3, :item4, :item5)
                """),
                {**p, "match_id": match_id},
            )
