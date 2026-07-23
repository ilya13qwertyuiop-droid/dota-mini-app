"""UTC week boundaries used for repeatable completed-week collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class CompletedWeek:
    """A Monday-to-Monday UTC interval which has already ended."""

    start: datetime
    end: datetime

    @property
    def iso_year(self) -> int:
        return self.start.isocalendar().year

    @property
    def iso_week(self) -> int:
        return self.start.isocalendar().week

    def substitutions(self) -> dict[str, str | int]:
        """Values accepted in a request-template JSON file."""
        return {
            "week_start": self.start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "week_end": self.end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "week_iso": f"{self.iso_year}-W{self.iso_week:02d}",
            "week_year": self.iso_year,
            "week_number": self.iso_week,
        }


def last_completed_weeks(count: int, *, now: datetime | None = None) -> list[CompletedWeek]:
    """Return completed UTC weeks, oldest first, excluding the current week."""
    if count < 1:
        raise ValueError("count must be at least 1")

    current = (now or datetime.now(UTC)).astimezone(UTC)
    current_monday = (current - timedelta(
        days=current.weekday(),
        hours=current.hour,
        minutes=current.minute,
        seconds=current.second,
        microseconds=current.microsecond,
    ))
    return [
        CompletedWeek(
            start=current_monday - timedelta(days=7 * offset),
            end=current_monday - timedelta(days=7 * (offset - 1)),
        )
        for offset in range(count, 0, -1)
    ]
