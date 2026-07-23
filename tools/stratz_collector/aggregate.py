"""Normalization and weighted aggregation of weekly STRATZ exports."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any

from .models import Matchups, PairStat


class DataShapeError(ValueError):
    """A GraphQL response does not have the configured, expected shape."""


def _as_id(value: Any, *, field: str) -> str:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise DataShapeError(f"{field} must be an integer hero id, got {value!r}") from exc
    if parsed <= 0:
        raise DataShapeError(f"{field} must be positive, got {parsed}")
    return str(parsed)


def _as_pair_stat(item: Mapping[str, Any], *, synergy_field: str, match_count_field: str) -> PairStat:
    try:
        synergy = float(item[synergy_field])
        match_count = int(item[match_count_field])
    except (KeyError, TypeError, ValueError) as exc:
        raise DataShapeError("pair entry has invalid synergy or matchCount") from exc
    if not isfinite(synergy):
        raise DataShapeError("pair synergy must be finite")
    if match_count < 0:
        raise DataShapeError("pair matchCount must not be negative")
    return PairStat(synergy=synergy, match_count=match_count)


def parse_week(rows: Any, hero_ids: Iterable[str], *, description: str) -> Matchups:
    """Parse one ``heroStats.matchUp`` snapshot into the legacy file shape."""
    if not isinstance(rows, list) or not rows:
        raise DataShapeError(f"STRATZ returned an empty matchUp for {description}")
    allowed = set(hero_ids)
    result: Matchups = {hero_id: {"vs": {}, "with": {}} for hero_id in allowed}

    for row in rows:
        if not isinstance(row, Mapping):
            raise DataShapeError(f"matchUp record for {description} must be an object")
        source_id = _as_id(row.get("heroId"), field="heroId")
        if source_id not in allowed:
            continue
        for kind in ("vs", "with"):
            raw_pairs = row.get(kind)
            if not isinstance(raw_pairs, list):
                raise DataShapeError(f"{kind} for hero {source_id} must be a list")
            for raw_pair in raw_pairs:
                if not isinstance(raw_pair, Mapping):
                    raise DataShapeError(f"{kind} contains a non-object pair")
                left = _as_id(raw_pair.get("heroId1"), field="heroId1")
                right = _as_id(raw_pair.get("heroId2"), field="heroId2")
                if left == source_id and right != source_id:
                    target_id = right
                elif right == source_id and left != source_id:
                    target_id = left
                else:
                    raise DataShapeError(
                        f"pair {left}/{right} is not attached to hero {source_id}"
                    )
                if target_id not in allowed:
                    continue
                if target_id in result[source_id][kind]:
                    raise DataShapeError(
                        f"duplicate {kind} pair {source_id}->{target_id} for {description}"
                    )
                result[source_id][kind][target_id] = _as_pair_stat(
                    raw_pair, synergy_field="synergy", match_count_field="matchCount"
                )
    return result


def aggregate_weeks(weeks: Iterable[Matchups], hero_ids: Iterable[str]) -> Matchups:
    """Merge weekly data using ``matchCount`` as the weight for synergy."""
    result: Matchups = {hero_id: {"vs": {}, "with": {}} for hero_id in hero_ids}
    for week in weeks:
        for hero_id, maps in week.items():
            target = result.setdefault(hero_id, {"vs": {}, "with": {}})
            for kind in ("vs", "with"):
                for other_id, stat in maps.get(kind, {}).items():
                    previous = target[kind].get(other_id)
                    if previous is None:
                        target[kind][other_id] = stat
                        continue
                    total_count = previous.match_count + stat.match_count
                    if total_count == 0:
                        target[kind][other_id] = PairStat(0.0, 0)
                    else:
                        weighted = (
                            previous.synergy * previous.match_count
                            + stat.synergy * stat.match_count
                        ) / total_count
                        target[kind][other_id] = PairStat(round(weighted, 3), total_count)
    return {
        hero_id: {
            kind: {
                other_id: stat for other_id, stat in maps[kind].items()
                if stat.match_count > 0
            }
            for kind in ("vs", "with")
        }
        for hero_id, maps in result.items()
    }


def to_jsonable(matchups: Matchups) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    """Produce exactly the legacy ``hero_matchups.json`` object shape."""
    return {
        hero_id: {
            kind: {
                other_id: {"synergy": stat.synergy, "matchCount": stat.match_count}
                for other_id, stat in sorted(pairs.items(), key=lambda item: int(item[0]))
            }
            for kind, pairs in (("vs", maps["vs"]), ("with", maps["with"]))
        }
        for hero_id, maps in sorted(matchups.items(), key=lambda item: int(item[0]))
    }
