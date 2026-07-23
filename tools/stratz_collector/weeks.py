"""STRATZ completed-week selection used by the existing browser collector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Any

from .aggregate import DataShapeError


SECONDS_PER_WEEK = 604_800


@dataclass(frozen=True)
class StratzWeek:
    """A completed STRATZ week represented by its integer week number."""

    number: int

    @property
    def timestamp(self) -> int:
        """The value expected by ``heroStats.matchUp(week: Long!)``."""
        return self.number * SECONDS_PER_WEEK

    @property
    def date(self) -> str:
        return datetime.fromtimestamp(self.timestamp, UTC).date().isoformat()


def completed_weeks_from_stats(rows: Any, count: int = 3) -> list[StratzWeek]:
    """Return the last ``count`` completed weeks, excluding the current one.

    STRATZ exposes its own monotonically increasing week number.  Using the
    maximum returned by ``heroStats.stats`` exactly matches the existing
    browser script and avoids assuming calendar-week semantics.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    if not isinstance(rows, list) or not rows:
        raise DataShapeError("STRATZ returned no heroStats.stats rows")

    numbers: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            number = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if number > 0 and isfinite(number):
            numbers.add(number)
    if not numbers:
        raise DataShapeError("could not determine the current STRATZ week")
    current_week = max(numbers)
    return [StratzWeek(number=current_week - offset) for offset in range(1, count + 1)]
