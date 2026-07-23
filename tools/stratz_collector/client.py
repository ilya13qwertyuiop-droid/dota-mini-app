"""Small resilient HTTP client for STRATZ GraphQL."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


class StratzRequestError(RuntimeError):
    """STRATZ did not return a usable GraphQL response after retries."""


class StratzClient:
    def __init__(
        self,
        token: str,
        *,
        endpoint: str = "https://api.stratz.com/graphql",
        attempts: int = 4,
        timeout: float = 30.0,
    ) -> None:
        if not token.strip():
            raise ValueError("STRATZ token must not be empty")
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self._token = token
        self._endpoint = endpoint
        self._attempts = attempts
        self._timeout = timeout

    async def execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
            for attempt in range(1, self._attempts + 1):
                try:
                    response = await client.post(self._endpoint, json=payload)
                except httpx.TransportError as exc:
                    if attempt == self._attempts:
                        raise StratzRequestError("STRATZ network request failed") from exc
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self._attempts:
                        raise StratzRequestError(
                            f"STRATZ returned HTTP {response.status_code} after {attempt} attempts"
                        )
                    await asyncio.sleep(_retry_delay(response, attempt))
                    continue
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise StratzRequestError(f"STRATZ returned HTTP {response.status_code}") from exc
                try:
                    body = response.json()
                except ValueError as exc:
                    raise StratzRequestError("STRATZ returned invalid JSON") from exc
                if not isinstance(body, dict):
                    raise StratzRequestError("STRATZ response root is not an object")
                if body.get("errors"):
                    raise StratzRequestError("STRATZ GraphQL returned errors")
                return body
        raise AssertionError("unreachable")


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            except (TypeError, ValueError):
                pass
    return float(2 ** (attempt - 1))
