from __future__ import annotations

import json
import gzip
import unittest

from backend.fantasy_config import (
    FANTASY_ELIGIBILITY_OVERRIDES,
    FANTASY_POSITION_OVERRIDES,
    OPENDOTA_FANTASY_ROLES,
    current_roster_players,
    get_fantasy_config,
)
from backend.fantasy_metrics import compress_match_snapshot, extract_player_stats


class FantasyConfigTests(unittest.TestCase):
    def test_every_slot_has_a_compatible_metric(self):
        config = get_fantasy_config()
        metrics = {metric["id"]: metric for metric in config["metrics"]}

        self.assertEqual(len(metrics), len(config["metrics"]))
        self.assertEqual(OPENDOTA_FANTASY_ROLES[4], "mid")
        self.assertTrue(all(
            role in {"core", "mid", "support"}
            for role in FANTASY_POSITION_OVERRIDES.values()
        ))
        self.assertEqual(
            {role["id"] for role in config["roles"]},
            {"core", "mid", "support"},
        )
        for role in config["roles"]:
            self.assertGreater(len(role["slots"]), 0)
            for slot in role["slots"]:
                default = metrics[slot["default_metric"]]
                self.assertEqual(default["color"], slot["color"])
                self.assertIn(default["formula"]["type"], {"linear", "inverse"})

    def test_multiplier_config_is_safe_for_dynamic_ui(self):
        config = get_fantasy_config()
        mechanics = config["mechanics"]
        multiplier = mechanics["multiplier"]
        self.assertLessEqual(multiplier["min"], multiplier["default"])
        self.assertLessEqual(multiplier["default"], multiplier["max"])
        self.assertGreater(multiplier["step"], 0)

        emblems = mechanics["emblems"]
        self.assertLessEqual(emblems["min"], emblems["default"])
        self.assertLessEqual(emblems["default"], emblems["max"])
        for role in config["roles"]:
            self.assertGreaterEqual(len(role["slots"]), emblems["max"])

    def test_known_standin_is_not_eligible(self):
        self.assertIs(FANTASY_ELIGIBILITY_OVERRIDES[152455523], False)
        self.assertIs(FANTASY_ELIGIBILITY_OVERRIDES[60943014], False)

    def test_position_overrides_cover_known_opendota_gaps(self):
        expected = {
            126842529: "core",
            165564598: "core",
            56351509: "core",
            92487440: "core",
            203351055: "core",
            145957968: "core",
            480412663: "mid",
            106573901: "mid",
            301750126: "mid",
            154974246: "mid",
            324277900: "mid",
            116865891: "mid",
            93618577: "mid",
        }
        self.assertEqual(FANTASY_POSITION_OVERRIDES, expected)

    def test_current_roster_filter_uses_opendota_flag(self):
        players = [
            {
                "account_id": 124801257,
                "name": "Nightfall",
                "is_current_team_member": True,
            },
            {
                "account_id": 152455523,
                "name": "V-Tune",
                "is_current_team_member": False,
            },
        ]
        self.assertEqual(
            current_roster_players(players),
            [{"account_id": 124801257, "name": "Nightfall"}],
        )


class FantasyExtractionTests(unittest.TestCase):
    def test_extracts_typed_metrics_and_keeps_numeric_snapshot(self):
        player = {
            "account_id": 42,
            "hero_id": 7,
            "duration": 2450,
            "win": 1,
            "kills": 10,
            "deaths": 2,
            "assists": 19,
            "last_hits": 401,
            "denies": 21,
            "gold_per_min": 721,
            "xp_per_min": 804,
            "net_worth": 30100,
            "hero_damage": 45678,
            "hero_healing": 1234,
            "tower_damage": 9876,
            "stuns": 18.25,
            "obs_placed": 3,
            "sen_placed": 4,
            "camps_stacked": 5,
            "rune_pickups": 12,
            "teamfight_participation": 0.73,
            "courier_kills": 1,
            "firstblood_claimed": 1,
            "buyback_count": 2,
            "tower_kills": 3,
            "roshans_killed": 1,
            "item_uses": {
                "smoke_of_deceit": 2,
                "famango": 1,
                "greater_famango": 2,
                "not_numeric": "skip",
            },
            "ability_uses": {"ability_lamp_use": 3},
            "killed": {"npc_dota_miniboss": 1},
            "chat": [{"key": "must not be stored"}],
        }

        stats = extract_player_stats(player)

        self.assertEqual(stats["smokes_used"], 2)
        self.assertEqual(stats["watchers_taken"], 3)
        self.assertEqual(stats["tormentor_kills"], 1)
        self.assertEqual(stats["lotuses_used"], 3)
        self.assertEqual(stats["roshan_kills"], 1)
        self.assertAlmostEqual(stats["teamfight_participation"], 0.73)

        snapshot = json.loads(stats["metrics_json"])
        self.assertEqual(snapshot["schema"], 1)
        self.assertEqual(snapshot["scalars"]["hero_damage"], 45678)
        self.assertEqual(
            snapshot["counters"]["item_uses"]["smoke_of_deceit"],
            2,
        )
        self.assertNotIn("chat", snapshot)
        self.assertNotIn("not_numeric", snapshot["counters"]["item_uses"])

        compressed = compress_match_snapshot({"match_id": 99, "players": [player]})
        restored = json.loads(gzip.decompress(compressed).decode("utf-8"))
        self.assertEqual(restored["match_id"], 99)
        self.assertEqual(restored["players"][0]["chat"][0]["key"], "must not be stored")


if __name__ == "__main__":
    unittest.main()
