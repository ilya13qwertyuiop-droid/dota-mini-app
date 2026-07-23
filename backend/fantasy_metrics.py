"""Чистое извлечение расширенных Fantasy-показателей из игрока OpenDota."""

from __future__ import annotations

import gzip
import json
import math
import re


def _num(value, default=0):
    """Числовые поля OpenDota периодически бывают null."""
    return default if value is None else value


_SAFE_COUNTER_KEY = re.compile(r"^[a-zA-Z0-9_.-]{1,96}$")
_COUNTER_MAPS = (
    "item_uses",
    "purchase",
    "ability_uses",
    "killed",
    "killed_by",
    "runes",
)


def _finite_number(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    return None


def _numeric_map(value: object) -> dict[str, int | float]:
    """Оставить только компактные числовые counters из вложенного OpenDota."""
    if not isinstance(value, dict):
        return {}
    result: dict[str, int | float] = {}
    for key, raw in list(value.items())[:256]:
        number = _finite_number(raw)
        if number is not None and _SAFE_COUNTER_KEY.fullmatch(str(key)):
            result[str(key)] = number
    return result


def _counter(player: dict, group: str, *keys: str) -> int:
    values = _numeric_map(player.get(group))
    return int(sum(float(values.get(key, 0)) for key in keys))


def _metrics_snapshot(player: dict) -> str:
    """Сохранить ограниченный по размеру снимок без таймлайнов и чата."""
    scalars: dict[str, int | float] = {}
    for key, raw in player.items():
        number = _finite_number(raw)
        if number is not None and _SAFE_COUNTER_KEY.fullmatch(str(key)):
            scalars[str(key)] = number
    counters = {
        group: values
        for group in _COUNTER_MAPS
        if (values := _numeric_map(player.get(group)))
    }
    return json.dumps(
        {"schema": 1, "scalars": scalars, "counters": counters},
        ensure_ascii=True,
        separators=(",", ":"),
    )


def extract_player_stats(player: dict) -> dict:
    """Вернуть типизированные поля БД и адаптивный JSON-снимок."""
    lotuses_used = _counter(
        player,
        "item_uses",
        "famango",
        "greater_famango",
        "great_famango",
    )
    return {
        "kills": int(_num(player.get("kills"))),
        "deaths": int(_num(player.get("deaths"))),
        "assists": int(_num(player.get("assists"))),
        "last_hits": int(_num(player.get("last_hits"))),
        "denies": int(_num(player.get("denies"))),
        "gold_per_min": int(_num(player.get("gold_per_min"))),
        "xp_per_min": int(_num(player.get("xp_per_min"))),
        "net_worth": int(_num(player.get("net_worth"))),
        "hero_damage": int(_num(player.get("hero_damage"))),
        "hero_healing": int(_num(player.get("hero_healing"))),
        "tower_damage": int(_num(player.get("tower_damage"))),
        "stuns": float(_num(player.get("stuns"), 0.0)),
        "obs_placed": int(_num(player.get("obs_placed"))),
        "sen_placed": int(_num(player.get("sen_placed"))),
        "camps_stacked": int(_num(player.get("camps_stacked"))),
        "rune_pickups": int(_num(player.get("rune_pickups"))),
        "teamfight_participation": float(
            _num(player.get("teamfight_participation"), 0.0)
        ),
        "courier_kills": int(_num(player.get("courier_kills"))),
        "firstblood_claimed": int(bool(player.get("firstblood_claimed"))),
        "smokes_used": _counter(player, "item_uses", "smoke_of_deceit"),
        # В OpenDota активация Watcher фиксируется как ability_lamp_use.
        "watchers_taken": _counter(player, "ability_uses", "ability_lamp_use"),
        # Название предмета менялось между патчами — складываем оба ключа.
        "madstones_used": _counter(
            player, "item_uses", "madstone", "item_madstone"
        ),
        "tormentor_kills": _counter(player, "killed", "npc_dota_miniboss"),
        # Это использованные healing lotus, не факт подбора с пруда.
        "lotuses_used": lotuses_used,
        "buyback_count": int(_num(player.get("buyback_count"))),
        "hero_id": int(_num(player.get("hero_id"))) or None,
        "duration": int(_num(player.get("duration"))),
        "win": int(_num(player.get("win"))),
        "tower_kills": int(
            _num(player.get("tower_kills", player.get("towers_killed")))
        ),
        "roshan_kills": int(
            _num(player.get("roshan_kills", player.get("roshans_killed")))
        ),
        "metrics_json": _metrics_snapshot(player),
    }


def compress_match_snapshot(match: dict) -> bytes:
    """Сжать полный публичный ответ OpenDota для будущих правил Fantasy.

    Это резерв для механик, которым понадобятся тайминги, teamfights,
    objectives, picks/bans или другие массивы, не вынесенные в SQL-колонки.
    """
    payload = json.dumps(
        match,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return gzip.compress(payload, compresslevel=6, mtime=0)
