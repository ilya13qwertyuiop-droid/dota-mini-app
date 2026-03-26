"""
Import dota2protracker build data into hero_builds_cache.

Usage:
    DATABASE_URL=postgresql+psycopg2://dotauser:password@localhost/dotadb \
        python -m backend.import_dota_builds
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from backend.stats_db import get_hero_build_cache, set_hero_build_cache


def main() -> None:
    builds_path = Path(__file__).resolve().parent.parent / "dota_builds.json"
    if not builds_path.exists():
        logger.error("dota_builds.json not found at %s", builds_path)
        sys.exit(1)

    logger.info("Loading %s …", builds_path)
    with open(builds_path, encoding="utf-8") as f:
        dota_builds: dict = json.load(f)

    total = len(dota_builds)
    updated = 0
    skipped = 0

    for hero_id_str, positions in dota_builds.items():
        hero_id = int(hero_id_str)

        cached = get_hero_build_cache(hero_id)
        if cached is None:
            logger.warning("hero_id=%d — no existing cache entry, skipping", hero_id)
            skipped += 1
            continue

        cached["dota_builds"] = positions
        set_hero_build_cache(hero_id, cached)
        updated += 1
        logger.info("hero_id=%d updated (%d positions)", hero_id, len(positions))

    logger.info("Done. total=%d updated=%d skipped=%d", total, updated, skipped)


if __name__ == "__main__":
    main()
