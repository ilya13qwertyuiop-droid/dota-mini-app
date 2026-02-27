"""
config.py — Project-wide constants for the Dota Mini App.

Unlike runtime settings (which are read from environment variables), these
constants are stable across environments and don't need to be overridden.
"""

# ---------------------------------------------------------------------------
# Game-mode allow-list — applied at ingestion time (stats_updater.py).
#
# Only matches whose (game_mode, lobby_type) pair appears in this set are
# written to the `matches` table.  Everything else is silently dropped
# before any DB write, so no API budget is wasted on junk modes.
#
# OpenDota numeric codes:
#   game_mode  1  = All Pick (unranked public)
#   game_mode  22 = Ranked All Pick
#   lobby_type  0 = public (unranked)
#   lobby_type  7 = ranked match
# ---------------------------------------------------------------------------

ALLOWED_GAME_MODE_PAIRS: frozenset[tuple[int, int]] = frozenset({
    (22, 7),   # Ranked All Pick — the only mode tracked for statistics
})

# ---------------------------------------------------------------------------
# Match quality filters — applied in the statistics layer (stats_db.py).
# Matches that pass the game-mode gate above are stored in `matches`.
# Only aggregate updates (hero_stats, hero_matchups, hero_synergy,
# match_players) additionally respect the duration limit below.
# ---------------------------------------------------------------------------

# Matches shorter than 15 minutes are considered analytically irrelevant:
# they typically represent early mass-disconnects, server crashes, or
# one-sided stomps where heroes never reached their power-spikes.
# Such matches skew win-rate and synergy data and are excluded from all
# hero analytics derived from our own match database.
MIN_MATCH_DURATION_SECONDS: int = 900  # 15 minutes
