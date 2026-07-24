"""Typed data structures shared by the collector modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class PairStat:
    """One directed hero-pair statistic from STRATZ."""

    synergy: float
    match_count: int


HeroPairs: TypeAlias = dict[str, dict[str, PairStat]]
Matchups: TypeAlias = dict[str, HeroPairs]
