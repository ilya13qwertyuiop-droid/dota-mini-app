from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from tools.stratz_collector.aggregate import DataShapeError, aggregate_weeks, normalize_records, to_jsonable
from tools.stratz_collector.client import _retry_delay
from tools.stratz_collector.template import RequestTemplate
from tools.stratz_collector.validate import validate_against_reference
from tools.stratz_collector.weeks import last_completed_weeks


def _week(synergy: float, matches: int) -> dict:
    return normalize_records(
        [{"hero": 1, "vs": [{"other": 2, "synergy": synergy, "matchCount": matches}],
          "with": [{"other": 2, "synergy": synergy, "matchCount": matches}]},
         {"hero": 2, "vs": [{"other": 1, "synergy": -synergy, "matchCount": matches}],
          "with": [{"other": 1, "synergy": synergy, "matchCount": matches}]}],
        hero_id_field="hero", pair_id_field="other", vs_field="vs", with_field="with",
    )


class AggregationTests(unittest.TestCase):
    def test_aggregation_uses_match_count_as_weight(self):
        result = aggregate_weeks([_week(2.0, 100), _week(8.0, 300)])
        pair = result["1"]["vs"]["2"]
        self.assertEqual(pair.match_count, 400)
        self.assertEqual(pair.synergy, 6.5)
        self.assertEqual(to_jsonable(result)["1"]["vs"]["2"],
                         {"synergy": 6.5, "matchCount": 400})

    def test_duplicate_pair_is_rejected(self):
        with self.assertRaises(DataShapeError):
            normalize_records(
                [{"hero": 1, "vs": [{"other": 2, "synergy": 1, "matchCount": 1},
                                     {"other": 2, "synergy": 2, "matchCount": 2}], "with": []}],
                hero_id_field="hero", pair_id_field="other", vs_field="vs", with_field="with",
            )


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


class TemplateAndWeekTests(unittest.TestCase):
    def test_template_substitutes_week_values_without_touching_query(self):
        raw = {
            "query": "query Test { heroStats { heroId } }",
            "variables": {"start": "{{week_start}}", "week": "{{week_number}}"},
            "records_path": "data.rows",
            "hero_id_field": "hero", "pair_id_field": "other",
            "vs_field": "vs", "with_field": "with",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "template.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            template = RequestTemplate.from_file(path)
        payload = template.payload({"week_start": "2026-07-06T00:00:00Z", "week_number": 28})
        self.assertEqual(payload["variables"], {"start": "2026-07-06T00:00:00Z", "week": 28})
        self.assertEqual(payload["query"], raw["query"])

    def test_current_week_is_excluded(self):
        weeks = last_completed_weeks(3, now=datetime(2026, 7, 23, 14, tzinfo=UTC))
        self.assertEqual([(week.start.date().isoformat(), week.end.date().isoformat()) for week in weeks], [
            ("2026-06-29", "2026-07-06"),
            ("2026-07-06", "2026-07-13"),
            ("2026-07-13", "2026-07-20"),
        ])


class ClientTests(unittest.TestCase):
    def test_retry_after_seconds_has_priority_over_backoff(self):
        import httpx

        response = httpx.Response(429, headers={"Retry-After": "7"})
        self.assertEqual(_retry_delay(response, attempt=3), 7.0)


if __name__ == "__main__":
    unittest.main()
