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

    # Migration: add rank_bucket column to DBs that predate this column.
    # We attempt the ALTER and silently ignore "duplicate column" errors.
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE matches ADD COLUMN rank_bucket VARCHAR(16)"))
        logger.info("[stats_db] Migration applied: added rank_bucket column to matches")
    except Exception:
        pass  # column already exists — nothing to do

    logger.info("[stats_db] Tables ready (matches, hero_matchups, hero_synergy, hero_stats)")


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
) -> None:
    """Atomically saves one match and updates all aggregate tables.

    Idempotent: uses INSERT ... ON CONFLICT (match_id) DO NOTHING and skips
    aggregate updates when the row already existed (rowcount == 0).
    This syntax is identical in PostgreSQL 9.5+ and SQLite 3.24+.
    """
    with engine.begin() as conn:
        # ----- Insert match (idempotent) -----
        result = conn.execute(
            text("""
                INSERT INTO matches
                    (match_id, start_time, duration, patch, avg_rank_tier, rank_bucket,
                     radiant_win, radiant_heroes, dire_heroes)
                VALUES
                    (:match_id, :start_time, :duration, :patch, :avg_rank_tier, :rank_bucket,
                     :radiant_win, :radiant_heroes, :dire_heroes)
                ON CONFLICT (match_id) DO NOTHING
            """),
            {
                "match_id": match_id,
                "start_time": start_time,
                "duration": duration,
                "patch": patch,
                "avg_rank_tier": avg_rank_tier,
                "rank_bucket": rank_bucket,
                "radiant_win": int(radiant_win),
                "radiant_heroes": json.dumps(radiant_heroes),
                "dire_heroes": json.dumps(dire_heroes),
            },
        )

        if result.rowcount == 0:
            # Match already in DB — skip aggregate updates to keep counts correct
            return

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
        # Delete the unwanted matches
        conn.execute(
            text("DELETE FROM matches WHERE match_id = :id"),
            [{"id": mid} for mid in match_ids],
        )

        # Wipe all aggregates
        conn.execute(text("DELETE FROM hero_matchups"))
        conn.execute(text("DELETE FROM hero_synergy"))
        conn.execute(text("DELETE FROM hero_stats"))

        # Load all remaining matches
        remaining = conn.execute(
            text("SELECT radiant_win, radiant_heroes, dire_heroes FROM matches")
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
