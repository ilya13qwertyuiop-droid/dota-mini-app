import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from backend.db import get_hero_matchups_from_cache, replace_hero_matchups_in_cache
from backend.opendota_client import get_hero_matchups as fetch_from_api

logger = logging.getLogger(__name__)

# TTL кэша в часах (по умолчанию 24, переопределяется через env)
CACHE_TTL_HOURS = int(os.getenv("HERO_MATCHUPS_TTL_HOURS", "24"))

# Параметры группировки
MIN_MATCHUPS_GAMES = int(os.getenv("HERO_MATCHUPS_MIN_GAMES", "100"))
WINRATE_STRONG_THRESHOLD = float(os.getenv("HERO_MATCHUPS_STRONG_THRESHOLD", "0.55"))
WINRATE_WEAK_THRESHOLD = float(os.getenv("HERO_MATCHUPS_WEAK_THRESHOLD", "0.45"))
MAX_MATCHUPS_PER_GROUP = int(os.getenv("HERO_MATCHUPS_MAX_PER_GROUP", "5"))


async def get_hero_matchups_cached(hero_id: int) -> list[dict]:
    """Возвращает матчапы героя, используя кэш в SQLite.

    Логика:
    - Кэш свежий (< TTL)  → возвращаем кэш (cache hit).
    - Кэш пустой / устарел → идём в OpenDota, обновляем кэш (cache miss).
    - OpenDota недоступен, но старый кэш есть → возвращаем устаревший кэш (stale fallback).
    - OpenDota недоступен, кэш пуст → пробрасываем исключение.
    """
    cached, last_updated = get_hero_matchups_from_cache(hero_id)

    # Определяем свежесть кэша
    cache_is_fresh = False
    if last_updated is not None:
        try:
            last_updated_dt = datetime.fromisoformat(last_updated)
            cache_is_fresh = (datetime.utcnow() - last_updated_dt) < timedelta(hours=CACHE_TTL_HOURS)
        except ValueError:
            pass  # некорректная дата → считаем кэш устаревшим

    if cache_is_fresh and cached:
        logger.info("[matchups cache] HIT  hero_id=%s (%d rows)", hero_id, len(cached))
        return sorted(cached, key=lambda x: x["winrate"], reverse=True)

    logger.info("[matchups cache] MISS hero_id=%s, fetching from OpenDota...", hero_id)

    try:
        api_data = await fetch_from_api(hero_id)
    except Exception as exc:
        if cached:
            logger.warning(
                "[matchups cache] OpenDota error (%s), returning stale cache for hero_id=%s",
                exc, hero_id,
            )
            return sorted(cached, key=lambda x: x["winrate"], reverse=True)
        raise

    # OpenDota возвращает: [{"hero_id": int, "games_played": int, "wins": int}, ...]
    now_iso = datetime.utcnow().isoformat()
    to_cache: list[dict] = []
    for entry in api_data:
        opponent_id = entry.get("hero_id")
        games = entry.get("games_played", 0)
        wins = entry.get("wins", 0)
        if not opponent_id or games == 0:
            continue
        to_cache.append({
            "opponent_hero_id": opponent_id,
            "games": games,
            "wins": wins,
            "winrate": round(wins / games, 4),
            "updated_at": now_iso,
        })

    replace_hero_matchups_in_cache(hero_id, to_cache, now_iso)
    logger.info("[matchups cache] stored %d rows for hero_id=%s", len(to_cache), hero_id)

    return sorted(to_cache, key=lambda x: x["winrate"], reverse=True)


def build_matchup_groups(matchups: list[dict], base_winrate: Optional[float]) -> dict:
    """Разбивает плоский список матчапов на strong_against и weak_against.

    Если base_winrate передан — считает advantage = winrate_vs - base_winrate
    и использует его для сортировки (аналог DotaBuff advantage).
    Если base_winrate is None — fallback на старую логику (только по winrate).
    """
    filtered = [m for m in matchups if m["games"] >= MIN_MATCHUPS_GAMES]

    if base_winrate is not None:
        logger.info("[matchups groups] base_winrate=%.4f, filtered=%d", base_winrate, len(filtered))

        # Добавляем advantage в копии записей (не мутируем оригинал кэша)
        enriched = []
        for m in filtered:
            entry = dict(m)
            entry["advantage"] = round(entry["winrate"] - base_winrate, 4)
            enriched.append(entry)

        # Диагностика: первые 3 значения
        sample = [(e["opponent_hero_id"], e["winrate"], e["advantage"]) for e in enriched[:3]]
        logger.info("[matchups groups] sample (id, wr, adv): %s", sample)

        strong_against = sorted(
            [e for e in enriched if e["advantage"] >= 0 and e["winrate"] >= WINRATE_STRONG_THRESHOLD],
            key=lambda x: x["advantage"],
            reverse=True,
        )[:MAX_MATCHUPS_PER_GROUP]

        weak_against = sorted(
            [e for e in enriched if e["advantage"] <= 0 and e["winrate"] <= WINRATE_WEAK_THRESHOLD],
            key=lambda x: x["advantage"],
        )[:MAX_MATCHUPS_PER_GROUP]

    else:
        # Fallback: base_winrate неизвестен — используем только winrate
        logger.warning("[matchups groups] base_winrate unavailable, fallback to winrate-only logic")

        strong_against = sorted(
            [m for m in filtered if m["winrate"] >= WINRATE_STRONG_THRESHOLD],
            key=lambda x: x["winrate"],
            reverse=True,
        )[:MAX_MATCHUPS_PER_GROUP]

        weak_against = sorted(
            [m for m in filtered if m["winrate"] <= WINRATE_WEAK_THRESHOLD],
            key=lambda x: x["winrate"],
        )[:MAX_MATCHUPS_PER_GROUP]

    base_wr_str = f"{base_winrate:.4f}" if base_winrate is not None else "None"
    logger.info(
        "[matchups groups] total=%d filtered(>=%dgames)=%d base_wr=%s strong=%d weak=%d",
        len(matchups), MIN_MATCHUPS_GAMES, len(filtered),
        base_wr_str, len(strong_against), len(weak_against),
    )
    return {"strong_against": strong_against, "weak_against": weak_against}
