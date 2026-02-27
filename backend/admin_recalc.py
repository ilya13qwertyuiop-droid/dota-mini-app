"""
admin_recalc.py — One-off script: rebuild all aggregate stats from scratch.

Wipes hero_stats, hero_matchups, hero_synergy and repopulates them from the
matches table, applying the MIN_MATCH_DURATION_SECONDS filter defined in
backend/config.py.  No match rows are deleted.

Usage (from project root):
    export DATABASE_URL="postgresql+psycopg2://user:pass@host/dbname"
    python -m backend.admin_recalc
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running as "python backend/admin_recalc.py" from project root too
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env if present (mirrors the pattern used by stats_updater.py)
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    # Import here so DATABASE_URL is already set from the environment / .env
    from backend.stats_db import recalculate_all_aggregates

    logger.info("admin_recalc: starting full aggregate recalculation")
    try:
        recalculate_all_aggregates()
        logger.info("admin_recalc: finished successfully")
    except Exception as exc:
        logger.error("admin_recalc: recalculation failed — %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
