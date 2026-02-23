import logging
import os

import httpx

logger = logging.getLogger(__name__)

OPENDOTA_API_KEY = os.getenv("OPENDOTA_API_KEY")
_BASE_URL = "https://api.opendota.com/api"


def _build_params() -> dict:
    """Добавляет api_key в query-параметры, если ключ задан."""
    if OPENDOTA_API_KEY:
        return {"api_key": OPENDOTA_API_KEY}
    return {}


async def get_heroes() -> list[dict]:
    """GET /api/heroes — возвращает список всех героев.

    Каждый элемент содержит поля: id, localized_name, primary_attr, и др.
    Поднимает RuntimeError при сетевых или API-ошибках.
    """
    url = f"{_BASE_URL}/heroes"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=_build_params(), timeout=15.0)
    except httpx.RequestError as e:
        logger.error("OpenDota network error (get_heroes): %s", e)
        raise RuntimeError(f"OpenDota network error: {e}") from e

    if r.status_code != 200:
        logger.error("OpenDota get_heroes returned HTTP %s: %s", r.status_code, r.text[:200])
        raise RuntimeError(f"OpenDota API returned HTTP {r.status_code}")

    return r.json()


async def get_hero_matchups(hero_id: int) -> list[dict]:
    """GET /api/heroes/{hero_id}/matchups — агрегированные матчапы героя.

    Каждый элемент содержит: hero_id, games_played, wins.
    Поднимает RuntimeError при сетевых или API-ошибках.
    """
    url = f"{_BASE_URL}/heroes/{hero_id}/matchups"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=_build_params(), timeout=15.0)
    except httpx.RequestError as e:
        logger.error("OpenDota network error (get_hero_matchups hero_id=%s): %s", hero_id, e)
        raise RuntimeError(f"OpenDota network error: {e}") from e

    if r.status_code != 200:
        logger.error(
            "OpenDota get_hero_matchups hero_id=%s returned HTTP %s: %s",
            hero_id, r.status_code, r.text[:200],
        )
        raise RuntimeError(f"OpenDota API returned HTTP {r.status_code}")

    return r.json()


