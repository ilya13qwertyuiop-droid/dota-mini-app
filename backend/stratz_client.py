import os

import httpx


STRATZ_API_URL = "https://api.stratz.com/graphql"


def get_stratz_headers() -> dict:
    """Возвращает заголовки для запросов к Stratz API."""
    token = os.environ.get("STRATZ_API_TOKEN")
    if not token:
        raise RuntimeError("STRATZ_API_TOKEN is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def execute_stratz_query(query: str, variables: dict | None = None) -> dict:
    """Выполняет GraphQL-запрос к Stratz API и возвращает поле data."""
    payload: dict = {"query": query}
    if variables is not None:
        payload["variables"] = variables

    headers = get_stratz_headers()

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                STRATZ_API_URL,
                json=payload,
                headers=headers,
                timeout=15.0,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"[STRATZ DEBUG] HTTP error {e.response.status_code}: {e.response.text[:200]}")
        raise RuntimeError(f"Stratz API returned HTTP {e.response.status_code}") from e
    except httpx.RequestError as e:
        print(f"[STRATZ DEBUG] Network error: {e}")
        raise RuntimeError(f"Stratz API network error: {e}") from e

    body: dict = r.json()

    if "errors" in body:
        errors = body["errors"]
        print(f"[STRATZ DEBUG] GraphQL errors: {errors}")
        raise RuntimeError(f"Stratz GraphQL error: {errors[0].get('message', errors)}")

    return body.get("data", {})
