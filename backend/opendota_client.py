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


async def get_hero_stats() -> list[dict]:
    """GET /api/heroStats — статистика всех героев по брекетам.

    Каждый объект содержит поля id, localized_name,
    и пары {N_pick, N_win} для N = 1..8 (ранговые брекеты).
    Поднимает RuntimeError при сетевых или API-ошибках.
    """
    url = f"{_BASE_URL}/heroStats"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=_build_params(), timeout=15.0)
    except httpx.RequestError as e:
        logger.error("OpenDota network error (get_hero_stats): %s", e)
        raise RuntimeError(f"OpenDota network error: {e}") from e

    if r.status_code != 200:
        logger.error("OpenDota get_hero_stats returned HTTP %s: %s", r.status_code, r.text[:200])
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


async def get_public_matches(less_than_match_id: int | None = None) -> list[dict]:
    """GET /api/publicMatches — recent public ranked matches.

    Params used: significant=1 (no turbo/practice), mmr_descending=1.
    Each entry contains:
      match_id, start_time, duration, radiant_win, avg_rank_tier,
      radiant_team (comma-sep hero IDs), dire_team (comma-sep hero IDs).

    Returns up to 100 matches per call.
    Raises RuntimeError on network or API errors.
    """
    url = f"{_BASE_URL}/publicMatches"
    params = _build_params()
    params["significant"] = 1
    params["mmr_descending"] = 1
    if less_than_match_id is not None:
        params["less_than_match_id"] = less_than_match_id

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, timeout=30.0)
    except httpx.RequestError as e:
        logger.error("OpenDota network error (get_public_matches): %s", e)
        raise RuntimeError(f"OpenDota network error: {e}") from e

    if r.status_code != 200:
        logger.error(
            "OpenDota get_public_matches returned HTTP %s: %s",
            r.status_code, r.text[:200],
        )
        raise RuntimeError(f"OpenDota API returned HTTP {r.status_code}")

    return r.json()


async def get_match_details(match_id: int) -> dict:
    """GET /api/matches/{match_id} — full match details.

    Key fields used by the stats layer:
      match_id, start_time, duration, patch, avg_rank_tier, radiant_win,
      players[].hero_id, players[].player_slot  (slot < 128 → Radiant).

    Raises RuntimeError on network or API errors.
    """
    url = f"{_BASE_URL}/matches/{match_id}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=_build_params(), timeout=30.0)
    except httpx.RequestError as e:
        logger.error("OpenDota network error (get_match_details match_id=%s): %s", match_id, e)
        raise RuntimeError(f"OpenDota network error: {e}") from e

    if r.status_code != 200:
        logger.error(
            "OpenDota get_match_details match_id=%s returned HTTP %s: %s",
            match_id, r.status_code, r.text[:200],
        )
        raise RuntimeError(f"OpenDota API returned HTTP {r.status_code}")

    return r.json()


