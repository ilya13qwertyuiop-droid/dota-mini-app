"""
hero_pairs.py — контрпики и синергия союзников для героя из hero_matchups.json
(Stratz-агрегаты). ЕДИНЫЙ источник для /api/hero/{id}/counters|synergy И для
бота (/counters, /synergy) — числа гарантированно совпадают с мини-апом.

Логика 1-в-1 повторяет прежние api-эндпоинты:
  wr_vs = base_wr + synergy/100;  advantage/delta = synergy/100.
counters: vs, advantage<=-0.002 (asc) / >=0.002 (desc).
synergy:  with, delta>=0 (desc) / <=0 (asc).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

# Бот импортит модули «голым» путём, api — пакетно (backend.*). Поддержим оба.
try:
    from backend.stats_db import get_hero_base_winrate_from_db, get_stats_mode
except ImportError:  # pragma: no cover
    from stats_db import get_hero_base_winrate_from_db, get_stats_mode

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_FILE = _ROOT / "hero_matchups.json"
_cache: dict | None = None


def _load() -> dict:
    """hero_matchups.json (Stratz), кэш на процесс."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_FILE, encoding="utf-8") as f:
            _cache = json.load(f)
    except Exception as e:
        logger.warning("[hero_pairs] hero_matchups.json read failed: %s", e)
        _cache = {}
    return _cache


def _base_wr(hero_id: int) -> tuple[float, bool]:
    strict = get_stats_mode() == "strict"
    bw = get_hero_base_winrate_from_db(hero_id, strict=strict)
    if bw is None:
        bw = 0.5
    return bw, strict


def get_hero_counters(hero_id: int, limit: int = 20, min_games: int = 50) -> dict:
    """{hero_id, base_winrate, data_games, counters, victims, strict_mode}."""
    base_wr, strict = _base_wr(hero_id)
    vs_map = (_load().get(str(hero_id)) or {}).get("vs") or {}

    enriched = []
    for opp_str, pair in vs_map.items():
        mc = int(pair.get("matchCount", 0))
        if mc < min_games:
            continue
        try:
            opp_id = int(opp_str)
        except (TypeError, ValueError):
            continue
        delta = float(pair.get("synergy", 0.0)) / 100.0
        enriched.append({
            "hero_id":       opp_id,
            "games":         mc,
            "wr_vs":         round(base_wr + delta, 4),
            "advantage":     round(delta, 4),
            "raw_advantage": round(delta, 4),
        })

    counters = sorted([e for e in enriched if e["advantage"] <= -0.002],
                      key=lambda x: x["advantage"])[:limit]
    victims = sorted([e for e in enriched if e["advantage"] >= 0.002],
                     key=lambda x: x["advantage"], reverse=True)[:limit]
    return {
        "hero_id": hero_id, "base_winrate": base_wr,
        "data_games": sum(e["games"] for e in enriched),
        "counters": counters, "victims": victims, "strict_mode": strict,
    }


def get_hero_synergy(hero_id: int, limit: int = 20, min_games: int = 50) -> dict:
    """{hero_id, base_winrate, data_games, best_allies, worst_allies, strict_mode}."""
    base_wr, strict = _base_wr(hero_id)
    with_map = (_load().get(str(hero_id)) or {}).get("with") or {}

    enriched = []
    for ally_str, pair in with_map.items():
        mc = int(pair.get("matchCount", 0))
        if mc < min_games:
            continue
        try:
            ally_id = int(ally_str)
        except (TypeError, ValueError):
            continue
        delta = float(pair.get("synergy", 0.0)) / 100.0
        wr_vs = base_wr + delta
        enriched.append({
            "hero_id":   ally_id,
            "games":     mc,
            "wins":      int(round(wr_vs * mc)),
            "wr_vs":     round(wr_vs, 4),
            "delta":     round(delta, 4),
            "advantage": round(delta, 4),
            "raw_delta": round(delta, 4),
        })

    best_allies = sorted([e for e in enriched if e["delta"] >= 0],
                         key=lambda x: x["delta"], reverse=True)[:limit]
    worst_allies = sorted([e for e in enriched if e["delta"] <= 0],
                          key=lambda x: x["delta"])[:limit]
    return {
        "hero_id": hero_id, "base_winrate": base_wr,
        "data_games": sum(e["games"] for e in enriched),
        "best_allies": best_allies, "worst_allies": worst_allies, "strict_mode": strict,
    }
