"""
stats_db.py — Database layer for the custom Dota 2 statistics collection.

Tables (all in the same dota_bot.db):
  matches        — raw match records
  hero_matchups  — hero A vs hero B (opponents), aggregated
  hero_synergy   — hero A with hero B (same team), aggregated
  hero_stats     — per-hero total games/wins across all matches

Key convention for matchup/synergy pairs:
  hero_a < hero_b  (canonical order, no duplicates)
  In hero_matchups, `wins` = wins by hero_a (the one with the smaller ID).
  When querying for hero X as hero_b, wr_x = (games - wins) / games.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "dota_bot.db"


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    # WAL mode: allows concurrent reads while the updater writes
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------

def init_stats_tables() -> None:
    """Creates all stats tables if they don't exist yet."""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id      INTEGER PRIMARY KEY,
            start_time    INTEGER NOT NULL,
            duration      INTEGER,
            patch         TEXT,
            avg_rank_tier INTEGER,
            rank_bucket   TEXT,
            radiant_win   INTEGER NOT NULL,
            radiant_heroes TEXT NOT NULL,
            dire_heroes    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hero_matchups (
            hero_a INTEGER NOT NULL,
            hero_b INTEGER NOT NULL,
            games  INTEGER NOT NULL DEFAULT 0,
            wins   INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (hero_a, hero_b)
        );

        CREATE TABLE IF NOT EXISTS hero_synergy (
            hero_a INTEGER NOT NULL,
            hero_b INTEGER NOT NULL,
            games  INTEGER NOT NULL DEFAULT 0,
            wins   INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (hero_a, hero_b)
        );

        CREATE TABLE IF NOT EXISTS hero_stats (
            hero_id INTEGER PRIMARY KEY,
            games   INTEGER NOT NULL DEFAULT 0,
            wins    INTEGER NOT NULL DEFAULT 0
        );
    """)

    conn.commit()

    # Migration: add rank_bucket to existing DBs that predate this column.
    # SQLite does not support ALTER TABLE ... ADD COLUMN IF NOT EXISTS before 3.37,
    # so we attempt the ALTER and silently ignore "duplicate column" errors.
    try:
        conn.execute("ALTER TABLE matches ADD COLUMN rank_bucket TEXT")
        conn.commit()
        logger.info("[stats_db] Migration applied: added rank_bucket column to matches")
    except sqlite3.OperationalError:
        pass  # column already exists — nothing to do

    conn.close()
    logger.info("[stats_db] Tables ready (matches, hero_matchups, hero_synergy, hero_stats)")


# ---------------------------------------------------------------------------
# Idempotent match ingestion
# ---------------------------------------------------------------------------

def match_exists(match_id: int) -> bool:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM matches WHERE match_id = ?", (match_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


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
    """
    Atomically saves one match and updates all aggregate tables.

    Idempotency: the caller is responsible for checking match_exists() first,
    OR let the INSERT fail on UNIQUE constraint (match_id is PK).
    To guarantee idempotency without a pre-check, we use INSERT OR IGNORE and
    only apply aggregate updates when a row is actually inserted.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        # Insert match; silently skip if already present (idempotent)
        cursor.execute(
            """
            INSERT OR IGNORE INTO matches
                (match_id, start_time, duration, patch, avg_rank_tier, rank_bucket,
                 radiant_win, radiant_heroes, dire_heroes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id, start_time, duration, patch, avg_rank_tier, rank_bucket,
                int(radiant_win),
                json.dumps(radiant_heroes),
                json.dumps(dire_heroes),
            ),
        )

        if cursor.rowcount == 0:
            # Match was already in DB — skip aggregate updates to keep counts correct
            conn.rollback()
            return

        # ---- hero_stats ----
        for h in radiant_heroes:
            cursor.execute(
                "INSERT INTO hero_stats (hero_id, games, wins) VALUES (?, 1, ?)"
                " ON CONFLICT(hero_id) DO UPDATE SET"
                "   games = games + 1,"
                "   wins  = wins  + excluded.wins",
                (h, int(radiant_win)),
            )
        for h in dire_heroes:
            cursor.execute(
                "INSERT INTO hero_stats (hero_id, games, wins) VALUES (?, 1, ?)"
                " ON CONFLICT(hero_id) DO UPDATE SET"
                "   games = games + 1,"
                "   wins  = wins  + excluded.wins",
                (h, int(not radiant_win)),
            )

        # ---- hero_matchups ----
        # For each (radiant_hero, dire_hero) pair:
        #   canonical pair: a = min(r, d), b = max(r, d)
        #   wins = wins for hero_a
        #   a_wins logic: if radiant won AND r is hero_a → a_wins=1
        #                 if dire won   AND d is hero_a → a_wins=1
        #   shorthand: a_wins = int((r < d) == radiant_win)
        for r_hero in radiant_heroes:
            for d_hero in dire_heroes:
                if r_hero == d_hero:
                    continue  # shouldn't happen, but be safe
                a = min(r_hero, d_hero)
                b = max(r_hero, d_hero)
                a_wins = int((r_hero < d_hero) == radiant_win)
                cursor.execute(
                    "INSERT INTO hero_matchups (hero_a, hero_b, games, wins) VALUES (?, ?, 1, ?)"
                    " ON CONFLICT(hero_a, hero_b) DO UPDATE SET"
                    "   games = games + 1,"
                    "   wins  = wins  + excluded.wins",
                    (a, b, a_wins),
                )

        # ---- hero_synergy ----
        # All C(5,2)=10 pairs within Radiant and within Dire
        for heroes, team_won in [
            (radiant_heroes, radiant_win),
            (dire_heroes, not radiant_win),
        ]:
            n = len(heroes)
            for i in range(n):
                for j in range(i + 1, n):
                    a = min(heroes[i], heroes[j])
                    b = max(heroes[i], heroes[j])
                    cursor.execute(
                        "INSERT INTO hero_synergy (hero_a, hero_b, games, wins) VALUES (?, ?, 1, ?)"
                        " ON CONFLICT(hero_a, hero_b) DO UPDATE SET"
                        "   games = games + 1,"
                        "   wins  = wins  + excluded.wins",
                        (a, b, int(team_won)),
                    )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reads for the API endpoint
# ---------------------------------------------------------------------------

def get_hero_matchup_rows(hero_id: int, min_games: int = 50) -> list[dict]:
    """
    Returns all opponent matchup rows for a hero.
    wins_for_hero = row.wins if hero_id==hero_a, else row.games - row.wins.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT hero_a, hero_b, games, wins FROM hero_matchups"
        " WHERE (hero_a = ? OR hero_b = ?) AND games >= ?",
        (hero_id, hero_id, min_games),
    )
    rows = cursor.fetchall()
    conn.close()

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
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT games, wins FROM hero_stats WHERE hero_id = ?", (hero_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row or row["games"] == 0:
        return None
    return round(row["wins"] / row["games"], 4)


def get_hero_total_games(hero_id: int) -> int:
    """Returns total number of games for a hero from hero_stats."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT games FROM hero_stats WHERE hero_id = ?", (hero_id,))
    row = cursor.fetchone()
    conn.close()
    return row["games"] if row else 0


def get_hero_synergy_rows(hero_id: int, min_games: int = 50) -> list[dict]:
    """
    Returns all ally synergy rows for a hero.

    Because both heroes are always on the same team, `wins` in hero_synergy
    is the count of wins for the shared team — it equals wins for either hero.
    So wr_with = wins / games regardless of canonical position.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT hero_a, hero_b, games, wins FROM hero_synergy"
        " WHERE (hero_a = ? OR hero_b = ?) AND games >= ?",
        (hero_id, hero_id, min_games),
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        hero_a, hero_b, games, wins = row["hero_a"], row["hero_b"], row["games"], row["wins"]
        ally_id = hero_b if hero_a == hero_id else hero_a
        result.append(
            {
                "hero_id": ally_id,
                "games": games,
                "wins": wins,
                # wr_vs keeps naming consistent with get_hero_matchup_rows
                # so the frontend renderMatchupList() can reuse the same field
                "wr_vs": round(wins / games, 4) if games > 0 else 0.0,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Cleanup & maintenance
# ---------------------------------------------------------------------------

def get_matches_count() -> int:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM matches")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_old_match_ids(older_than_days: int) -> list[int]:
    """Returns match_ids with start_time older than `older_than_days` days."""
    cutoff = int(time.time()) - older_than_days * 86400
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT match_id FROM matches WHERE start_time < ? ORDER BY start_time ASC",
        (cutoff,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_oldest_match_ids(count: int) -> list[int]:
    """Returns the `count` oldest match_ids (for max-cap enforcement)."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT match_id FROM matches ORDER BY start_time ASC LIMIT ?", (count,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def delete_matches_and_recalculate(match_ids: list[int]) -> None:
    """
    Deletes the specified matches then fully recalculates all aggregates
    from the remaining matches.

    Recalculation approach (accumulate in Python dicts → bulk INSERT) is
    faster than per-row upserts when many rows are deleted at once.
    """
    if not match_ids:
        return

    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        # Delete the unwanted matches
        cursor.executemany(
            "DELETE FROM matches WHERE match_id = ?",
            [(mid,) for mid in match_ids],
        )

        # Wipe all aggregates
        cursor.execute("DELETE FROM hero_matchups")
        cursor.execute("DELETE FROM hero_synergy")
        cursor.execute("DELETE FROM hero_stats")

        # Load all remaining matches
        cursor.execute(
            "SELECT radiant_win, radiant_heroes, dire_heroes FROM matches"
        )
        remaining = cursor.fetchall()

        # Accumulate in Python dicts (much faster than per-row upserts)
        matchups: dict[tuple[int, int], list[int]] = {}
        synergy: dict[tuple[int, int], list[int]] = {}
        stats: dict[int, list[int]] = {}

        for row in remaining:
            radiant_win = bool(row["radiant_win"])
            r_heroes: list[int] = json.loads(row["radiant_heroes"])
            d_heroes: list[int] = json.loads(row["dire_heroes"])

            # hero_stats
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

            # hero_matchups
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

            # hero_synergy
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
        cursor.executemany(
            "INSERT INTO hero_matchups (hero_a, hero_b, games, wins) VALUES (?, ?, ?, ?)",
            [(a, b, v[0], v[1]) for (a, b), v in matchups.items()],
        )
        cursor.executemany(
            "INSERT INTO hero_synergy (hero_a, hero_b, games, wins) VALUES (?, ?, ?, ?)",
            [(a, b, v[0], v[1]) for (a, b), v in synergy.items()],
        )
        cursor.executemany(
            "INSERT INTO hero_stats (hero_id, games, wins) VALUES (?, ?, ?)",
            [(h, v[0], v[1]) for h, v in stats.items()],
        )

        conn.commit()
        logger.info(
            "[stats_db] Cleanup done: deleted %d matches, remaining=%d,"
            " matchup_pairs=%d, synergy_pairs=%d",
            len(match_ids),
            len(remaining),
            len(matchups),
            len(synergy),
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
