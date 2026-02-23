import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from backend.opendota_client import get_hero_stats as fetch_hero_stats

logger = logging.getLogger(__name__)

HERO_STATS_TTL_HOURS = int(os.getenv("HERO_STATS_TTL_HOURS", "24"))

# In-memory кэш: hero_id -> base winrate (0..1)
_hero_winrates: dict[int, float] = {}
_last_updated: Optional[datetime] = None


def _is_cache_fresh() -> bool:
    if _last_updated is None:
        return False
    return (datetime.utcnow() - _last_updated) < timedelta(hours=HERO_STATS_TTL_HOURS)


async def _refresh_cache() -> None:
    """Загружает /heroStats из OpenDota и пересчитывает базовые винрейты."""
    global _hero_winrates, _last_updated

    raw = await fetch_hero_stats()

    new_winrates: dict[int, float] = {}
    for hero in raw:
        hero_id = hero.get("id")
        if not hero_id:
            continue
        total_pick = sum(hero.get(f"{n}_pick", 0) or 0 for n in range(1, 9))
        total_win = sum(hero.get(f"{n}_win", 0) or 0 for n in range(1, 9))
        if total_pick > 0:
            new_winrates[hero_id] = round(total_win / total_pick, 4)

    _hero_winrates = new_winrates
    _last_updated = datetime.utcnow()

    # Диагностический лог: сколько героев и пара примеров
    sample = list(new_winrates.items())[:3]
    logger.info(
        "[hero_stats] cache refreshed: %d heroes, TTL=%dh, sample=%s",
        len(new_winrates), HERO_STATS_TTL_HOURS, sample,
    )


async def get_hero_base_winrate(hero_id: int) -> Optional[float]:
    """Возвращает базовый паблик-винрейт героя (0..1) с in-memory кэшем.

    - Кэш свежий → отдаём из памяти.
    - Кэш устарел / пуст → обновляем из OpenDota.
    - OpenDota недоступен, а старый кэш есть → возвращаем из него (stale).
    - OpenDota недоступен и кэша нет → возвращаем None.
    """
    if not _is_cache_fresh():
        try:
            await _refresh_cache()
        except Exception as exc:
            if _hero_winrates:
                logger.warning(
                    "[hero_stats] OpenDota unavailable (%s), using stale cache (%d heroes)",
                    exc, len(_hero_winrates),
                )
            else:
                logger.error("[hero_stats] OpenDota unavailable and cache empty: %s", exc)
                return None

    wr = _hero_winrates.get(hero_id)
    if wr is None:
        logger.warning("[hero_stats] no base winrate for hero_id=%s", hero_id)
    return wr
