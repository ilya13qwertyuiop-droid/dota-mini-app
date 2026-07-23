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


def normalize_records(
    records: Iterable[Mapping[str, Any]],
    *,
    hero_id_field: str,
    pair_id_field: str,
    vs_field: str,
    with_field: str,
    synergy_field: str = "synergy",
    match_count_field: str = "matchCount",
) -> Matchups:
    """Turn configured GraphQL records into the application's JSON contract.

    The exact STRATZ query is deliberately supplied by a JSON request template.
    This adapter keeps the project format independent of STRATZ's response names.
    """
    result: Matchups = {}
    for raw_hero in records:
        hero_id = _as_id(raw_hero.get(hero_id_field), field=hero_id_field)
        if hero_id in result:
            raise DataShapeError(f"duplicate hero {hero_id}")
        hero_result: dict[str, dict[str, PairStat]] = {"vs": {}, "with": {}}
        for source_field, target_field in ((vs_field, "vs"), (with_field, "with")):
            raw_pairs = raw_hero.get(source_field, [])
            if not isinstance(raw_pairs, list):
                raise DataShapeError(f"{source_field} for hero {hero_id} must be a list")
            for raw_pair in raw_pairs:
                if not isinstance(raw_pair, Mapping):
                    raise DataShapeError(f"{source_field} contains a non-object pair")
                other_id = _as_id(raw_pair.get(pair_id_field), field=pair_id_field)
                if other_id == hero_id:
                    continue
                if other_id in hero_result[target_field]:
                    raise DataShapeError(
                        f"duplicate {target_field} pair {hero_id}->{other_id}"
                    )
                hero_result[target_field][other_id] = _as_pair_stat(
                    raw_pair,
                    synergy_field=synergy_field,
                    match_count_field=match_count_field,
                )
        result[hero_id] = hero_result
    if not result:
        raise DataShapeError("GraphQL response contains no hero records")
    return result


def aggregate_weeks(weeks: Iterable[Matchups]) -> Matchups:
    """Merge weekly data using ``matchCount`` as the weight for synergy."""
    result: Matchups = {}
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
                        target[kind][other_id] = PairStat(weighted, total_count)
    return result


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
