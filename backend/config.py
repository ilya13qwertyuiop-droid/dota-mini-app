"""
config.py — Project-wide constants for the Dota Mini App.

Unlike runtime settings (which are read from environment variables), these
constants are stable across environments and don't need to be overridden.
"""

# ---------------------------------------------------------------------------
# Match quality filters — applied in the statistics layer (stats_db.py).
# Raw rows are always stored in the matches table; only aggregate updates
# (hero_stats, hero_matchups, hero_synergy, match_players) respect this limit.
# ---------------------------------------------------------------------------

# Matches shorter than 15 minutes are considered analytically irrelevant:
# they typically represent early mass-disconnects, server crashes, or
# one-sided stomps where heroes never reached their power-spikes.
# Such matches skew win-rate and synergy data and are excluded from all
# hero analytics derived from our own match database.
MIN_MATCH_DURATION_SECONDS: int = 900  # 15 minutes
