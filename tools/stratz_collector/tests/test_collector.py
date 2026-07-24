from __future__ import annotations

import unittest

from tools.stratz_collector.aggregate import DataShapeError, aggregate_weeks, parse_week, to_jsonable
from tools.stratz_collector.client import _retry_delay
from tools.stratz_collector.validate import validate_against_reference
from tools.stratz_collector.weeks import completed_weeks_from_stats


def _week(synergy: float, matches: int) -> dict:
    return parse_week(
        [{"heroId": 1, "vs": [{"heroId1": 1, "heroId2": 2, "synergy": synergy, "matchCount": matches}],
          "with": [{"heroId1": 1, "heroId2": 2, "synergy": synergy, "matchCount": matches}]},
         {"heroId": 2, "vs": [{"heroId1": 1, "heroId2": 2, "synergy": -synergy, "matchCount": matches}],
          "with": [{"heroId1": 1, "heroId2": 2, "synergy": synergy, "matchCount": matches}]}],
        ["1", "2"], description="test",
    )


class AggregationTests(unittest.TestCase):
    def test_aggregation_uses_match_count_as_weight(self):
        result = aggregate_weeks([_week(2.0, 100), _week(8.0, 300)], ["1", "2"])
        pair = result["1"]["vs"]["2"]
        self.assertEqual(pair.match_count, 400)
        self.assertEqual(pair.synergy, 6.5)
        self.assertEqual(to_jsonable(result)["1"]["vs"]["2"],
                         {"synergy": 6.5, "matchCount": 400})

    def test_duplicate_pair_is_rejected(self):
        with self.assertRaises(DataShapeError):
            parse_week(
                [{"heroId": 1, "vs": [{"heroId1": 1, "heroId2": 2, "synergy": 1, "matchCount": 1},
                                         {"heroId1": 1, "heroId2": 2, "synergy": 2, "matchCount": 2}], "with": []}],
                ["1", "2"], description="test",
            )

    def test_rows_outside_reference_are_ignored(self):
        data = parse_week(
            [{"heroId": 0, "vs": [], "with": []},
             {"heroId": 1, "vs": [{"heroId1": 1, "heroId2": 2, "synergy": 1, "matchCount": 1}],
              "with": [{"heroId1": 1, "heroId2": 2, "synergy": 1, "matchCount": 1}]}],
            ["1", "2"], description="test",
        )
        self.assertEqual(data["1"]["vs"]["2"].synergy, 1)


class ValidationTests(unittest.TestCase):
    def test_missing_pair_is_rejected(self):
        reference = _week(1.0, 1000)
        candidate = _week(1.0, 1000)
        del candidate["1"]["vs"]["2"]
        with self.assertRaisesRegex(DataShapeError, "hero-pair set differs"):
            validate_against_reference(candidate, reference)

    def test_report_counts_low_samples(self):
        data = _week(1.0, 100)
        report = validate_against_reference(data, data)
        self.assertEqual(report.hero_count, 2)
        self.assertEqual(report.pair_count, 4)
        self.assertEqual(report.low_sample_pairs, 4)


class WeekTests(unittest.TestCase):
    def test_current_stratz_week_is_excluded(self):
        weeks = completed_weeks_from_stats([{"week": 2923}, {"week": 2922}, {"week": 2923}], 3)
        self.assertEqual([week.number for week in weeks], [2922, 2921, 2920])
        self.assertEqual([week.timestamp for week in weeks], [
            2922 * 604800, 2921 * 604800, 2920 * 604800,
        ])


class ClientTests(unittest.TestCase):
    def test_retry_after_seconds_has_priority_over_backoff(self):
        import httpx

        response = httpx.Response(429, headers={"Retry-After": "7"})
        self.assertEqual(_retry_delay(response, attempt=3), 7.0)


if __name__ == "__main__":
    unittest.main()
