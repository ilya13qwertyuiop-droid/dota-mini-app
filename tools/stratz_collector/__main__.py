"""CLI entry point for collecting validated STRATZ hero-pair data locally."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from .aggregate import DataShapeError, aggregate_weeks, parse_week, to_jsonable
from .client import StratzClient, StratzRequestError
from .queries import MATCHUP_QUERY, STATS_QUERY
from .validate import load_legacy_file, validate_against_reference
from .weeks import completed_weeks_from_stats

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect and validate STRATZ data into hero_matchups.json format."
    )
    parser.add_argument("--reference", required=True, type=Path,
                        help="Current known-good hero_matchups.json.")
    parser.add_argument("--output", required=True, type=Path,
                        help="Destination; is atomically replaced only after validation.")
    parser.add_argument("--weeks", type=int, default=3,
                        help="Number of completed STRATZ weeks to aggregate (default: 3).")
    parser.add_argument("--token-env", default="STRATZ_API_TOKEN",
                        help="Environment variable containing the STRATZ token.")
    parser.add_argument("--endpoint", default="https://api.stratz.com/graphql",
                        help="STRATZ GraphQL endpoint.")
    parser.add_argument("--attempts", type=int, default=5,
                        help="Network / 429 / 5xx attempts per request (default: 5).")
    parser.add_argument("--request-delay", type=float, default=0.8,
                        help="Pause between weekly GraphQL queries in seconds (default: .8).")
    parser.add_argument("--max-total-match-delta", type=float, default=0.25,
                        help="Maximum allowed total matchCount change from reference (default: .25).")
    return parser


async def _collect(args: argparse.Namespace) -> None:
    token = os.environ.get(args.token_env, "")
    if not token:
        raise DataShapeError(f"environment variable {args.token_env} is not set")
    reference = load_legacy_file(args.reference)
    client = StratzClient(token, endpoint=args.endpoint, attempts=args.attempts)

    stats = await client.execute({"query": STATS_QUERY, "variables": {}})
    try:
        weeks = completed_weeks_from_stats(stats["data"]["heroStats"]["stats"], args.weeks)
    except (KeyError, TypeError) as exc:
        raise DataShapeError("STRATZ stats response has an unexpected shape") from exc

    weekly_data = []
    hero_ids = reference.keys()
    for index, week in enumerate(weeks):
        if index:
            await asyncio.sleep(args.request_delay)
        logger.info("collecting %s (STRATZ week %d): %d/%d", week.date, week.number,
                    index + 1, len(weeks))
        matchup = await client.execute({
            "query": MATCHUP_QUERY,
            "variables": {"week": week.timestamp},
        })
        try:
            rows = matchup["data"]["heroStats"]["matchUp"]
        except (KeyError, TypeError) as exc:
            raise DataShapeError("STRATZ matchUp response has an unexpected shape") from exc
        weekly_data.append(parse_week(rows, hero_ids, description=f"{week.date}, week {week.number}"))

    candidate = aggregate_weeks(weekly_data, hero_ids)
    report = validate_against_reference(
        candidate, reference, max_total_match_delta=args.max_total_match_delta
    )
    _atomic_json_write(args.output, to_jsonable(candidate))
    logger.info(
        "saved %s: heroes=%d pairs=%d total_matchCount=%d low_samples=%d asymmetric=%d",
        args.output, report.hero_count, report.pair_count, report.total_matches,
        report.low_sample_pairs, report.asymmetric_pairs,
    )


def _atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temp:
        json.dump(payload, temp, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        temp.write("\n")
        temporary_path = Path(temp.name)
    temporary_path.replace(path)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parser().parse_args()
    try:
        asyncio.run(_collect(args))
    except (DataShapeError, StratzRequestError, ValueError) as exc:
        logger.error("collector stopped without changing the output: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
