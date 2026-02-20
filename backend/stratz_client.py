import os

import httpx


STRATZ_API_URL = "https://api.stratz.com/graphql"

VALID_RANKS = frozenset({"HERALD_GUARDIAN", "CRUSADER_ARCHON", "LEGEND_ANCIENT", "DIVINE_IMMORTAL"})

MATCHLIMIT_BY_RANK: dict[str, int] = {
    "HERALD_GUARDIAN": 1000,
    "CRUSADER_ARCHON": 1500,
    "LEGEND_ANCIENT": 1500,
    "DIVINE_IMMORTAL": 500,
}

_HERO_VS_HERO_QUERY = """
query HeroVsHeroByRank($heroId: Short!, $brackets: [RankBracketBasicEnum!], $matchLimit: Int!) {
  heroStats {
    heroVsHeroMatchup(heroId: $heroId, bracketBasicIds: $brackets, matchLimit: $matchLimit) {
      advantage {
        with {
          heroId1
          heroId2
          matchCount
          winCount
          winRateHeroId1
          winRateHeroId2
          synergy
        }
      }
      disadvantage {
        vs {
          heroId1
          heroId2
          matchCount
          winCount
          winRateHeroId1
          winRateHeroId2
          synergy
        }
      }
    }
  }
}
"""

# Stratz стоит за Cloudflare. Без правдоподобного User-Agent
# WAF возвращает 403 + HTML-страницу (не GraphQL-ошибку).
_EXTRA_HEADERS = {
    "User-Agent": "STRATZ_API",
    "Accept": "application/json",
}


def get_stratz_headers() -> dict:
    """Возвращает заголовки для запросов к Stratz API."""
    token = os.environ.get("STRATZ_API_TOKEN")
    if not token:
        raise RuntimeError("STRATZ_API_TOKEN is not set")
    # Логируем только длину и первые 5 символов — токен не раскрываем
    print(f"[STRATZ DEBUG] Token loaded: len={len(token)}, prefix={token[:5]}***")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        **_EXTRA_HEADERS,
    }


async def get_hero_matchups(hero_id: int, rank: str) -> dict:
    """Запрашивает матчапы героя у STRATZ с фильтрацией по рангу.

    Возвращает поле data из ответа GraphQL (словарь).
    Поднимает RuntimeError при сетевых / API ошибках.
    """
    match_limit = MATCHLIMIT_BY_RANK[rank]
    variables: dict = {
        "heroId": hero_id,
        "brackets": [rank],
        "matchLimit": match_limit,
    }
    print(f"[STRATZ DEBUG] get_hero_matchups: hero_id={hero_id}, rank={rank}, matchLimit={match_limit}")
    return await execute_stratz_query(_HERO_VS_HERO_QUERY, variables=variables)


async def execute_stratz_query(query: str, variables: dict | None = None) -> dict:
    """Выполняет GraphQL-запрос к Stratz API и возвращает поле data."""
    payload: dict = {"query": query}
    if variables is not None:
        payload["variables"] = variables

    headers = get_stratz_headers()
    print(f"[STRATZ DEBUG] POST {STRATZ_API_URL} | variables={variables}")

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                STRATZ_API_URL,
                json=payload,
                headers=headers,
                timeout=15.0,
            )
    except httpx.RequestError as e:
        print(f"[STRATZ DEBUG] Network error: {e}")
        raise RuntimeError(f"Stratz API network error: {e}") from e

    # Логируем статус и начало тела — до raise_for_status, чтобы видеть контекст ошибки
    print(
        f"[STRATZ DEBUG] Response status={r.status_code} | "
        f"body[:150]={r.text[:150]!r}"
    )

    # 403 разбираем отдельно: HTML-тело → WAF/Cloudflare, JSON → проблема с токеном
    if r.status_code == 403:
        is_html = r.text.lstrip()[:9].lower().startswith(("<!doctype", "<html"))
        if is_html:
            print(
                "[STRATZ DEBUG] 403 + HTML body → скорее всего блокировка Cloudflare/WAF, "
                "а не проблема с правами токена. Причина: неподходящий User-Agent или IP."
            )
        else:
            print(
                "[STRATZ DEBUG] 403 + non-HTML body → вероятно невалидный или истёкший "
                "STRATZ_API_TOKEN, либо недостаточно прав."
            )
        raise RuntimeError(
            "Stratz API returned HTTP 403 – "
            "verify STRATZ_API_TOKEN validity and API access rights"
        )

    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(
            f"[STRATZ DEBUG] HTTP error {e.response.status_code}: "
            f"{e.response.text[:200]!r}"
        )
        raise RuntimeError(f"Stratz API returned HTTP {e.response.status_code}") from e

    body: dict = r.json()

    if "errors" in body:
        errors = body["errors"]
        print(f"[STRATZ DEBUG] GraphQL errors: {errors}")
        raise RuntimeError(f"Stratz GraphQL error: {errors[0].get('message', errors)}")

    return body.get("data", {})
