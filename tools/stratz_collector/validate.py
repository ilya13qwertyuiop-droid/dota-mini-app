"""Safety checks before a new matchups file can replace a known-good export."""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from .aggregate import DataShapeError, normalize_records
from .models import Matchups


@dataclass(frozen=True)
class ValidationReport:
    hero_count: int
    pair_count: int
    total_matches: int
    low_sample_pairs: int
    asymmetric_pairs: int


def load_legacy_file(path: Path) -> Matchups:
    """Load and validate a committed-format ``hero_matchups.json`` file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataShapeError(f"cannot read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise DataShapeError("reference file root must be an object")

    records: list[dict[str, Any]] = []
    for hero_id, maps in raw.items():
        if not isinstance(maps, dict):
            raise DataShapeError(f"hero {hero_id} must be an object")
        record: dict[str, Any] = {"hero": hero_id, "vs": [], "with": []}
        for kind in ("vs", "with"):
            pairs = maps.get(kind, {})
            if not isinstance(pairs, dict):
                raise DataShapeError(f"hero {hero_id}.{kind} must be an object")
            for other_id, stat in pairs.items():
                if not isinstance(stat, dict):
                    raise DataShapeError(f"hero {hero_id}.{kind}.{other_id} must be an object")
                record[kind].append({"other": other_id, **stat})
        records.append(record)
    return normalize_records(
        records,
        hero_id_field="hero",
        pair_id_field="other",
        vs_field="vs",
        with_field="with",
    )


def _all_pairs(matchups: Matchups) -> set[tuple[str, str, str]]:
    return {
        (hero_id, kind, other_id)
        for hero_id, maps in matchups.items()
        for kind in ("vs", "with")
        for other_id in maps[kind]
    }


def validate_against_reference(
    candidate: Matchups,
    reference: Matchups,
    *,
    max_total_match_delta: float = 0.25,
    low_sample_threshold: int = 500,
    asymmetry_threshold: float = 1.0,
) -> ValidationReport:
    """Reject incomplete or unexpectedly different exports.

    The collector treats a changed hero/pair set as a failure, rather than silently
    replacing production data with a partial STRATZ response.
    """
    if not 0 <= max_total_match_delta < 1:
        raise ValueError("max_total_match_delta must be in [0, 1)")
    if set(candidate) != set(reference):
        missing = sorted(set(reference) - set(candidate), key=int)
        extra = sorted(set(candidate) - set(reference), key=int)
        raise DataShapeError(f"hero set differs from reference; missing={missing}, extra={extra}")

    expected_pairs = _all_pairs(reference)
    candidate_pairs = _all_pairs(candidate)
    if candidate_pairs != expected_pairs:
        raise DataShapeError(
            "hero-pair set differs from reference; "
            f"missing={len(expected_pairs - candidate_pairs)}, "
            f"extra={len(candidate_pairs - expected_pairs)}"
        )

    total_matches = 0
    reference_matches = 0
    low_sample_pairs = 0
    asymmetric_pairs = 0
    for hero_id, kind, other_id in candidate_pairs:
        stat = candidate[hero_id][kind][other_id]
        ref = reference[hero_id][kind][other_id]
        if stat.match_count < 0 or not isfinite(stat.synergy):
            raise DataShapeError(f"invalid {kind} value for {hero_id}->{other_id}")
        total_matches += stat.match_count
        reference_matches += ref.match_count
        if stat.match_count < low_sample_threshold:
            low_sample_pairs += 1
        reverse = candidate.get(other_id, {}).get(kind, {}).get(hero_id)
        if reverse is not None:
            difference = abs(
                stat.synergy + reverse.synergy if kind == "vs"
                else stat.synergy - reverse.synergy
            )
            if difference > asymmetry_threshold:
                asymmetric_pairs += 1

    if reference_matches:
        delta = abs(total_matches - reference_matches) / reference_matches
        if delta > max_total_match_delta:
            raise DataShapeError(
                "total matchCount differs from reference by "
                f"{delta:.1%} (limit {max_total_match_delta:.1%})"
            )
    return ValidationReport(
        hero_count=len(candidate),
        pair_count=len(candidate_pairs),
        total_matches=total_matches,
        low_sample_pairs=low_sample_pairs,
        asymmetric_pairs=asymmetric_pairs,
    )
