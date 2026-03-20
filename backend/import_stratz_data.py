"""
Import Stratz data into hero_builds_cache.

Usage:
    DATABASE_URL=postgresql+psycopg2://dotauser:password@localhost/dotadb \
        python -m backend.import_stratz_data
"""

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from backend.stats_db import get_hero_build_cache, set_hero_build_cache


def main() -> None:
    stratz_path = Path(__file__).resolve().parent.parent / "stratz_data.json"
    if not stratz_path.exists():
        logger.error("stratz_data.json not found at %s", stratz_path)
        sys.exit(1)

    logger.info("Loading %s …", stratz_path)
    with open(stratz_path, encoding="utf-8") as f:
        stratz_data: dict = json.load(f)

    total = len(stratz_data)
    updated = 0
    skipped = 0

    for hero_id_str, ranks in stratz_data.items():
        hero_id = int(hero_id_str)

        cached = get_hero_build_cache(hero_id)
        if cached is None:
            logger.warning("hero_id=%d — no existing cache entry, skipping", hero_id)
            skipped += 1
            continue

        cached["stratz"] = ranks
        set_hero_build_cache(hero_id, cached)
        updated += 1
        logger.info("hero_id=%d updated", hero_id)

    logger.info("Done. total=%d updated=%d skipped=%d", total, updated, skipped)


if __name__ == "__main__":
    main()
