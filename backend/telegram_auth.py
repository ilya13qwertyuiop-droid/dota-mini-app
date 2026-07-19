"""Validation of signed Telegram Mini App launch data."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qsl


INIT_DATA_MAX_AGE_SECONDS = 600
INIT_DATA_MAX_FUTURE_SKEW_SECONDS = 300


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    now: float | None = None,
) -> dict[str, str] | None:
    """Return signed parameters or ``None`` for invalid/replayed payloads."""

    if not init_data or not bot_token:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except (TypeError, ValueError):
        return None

    # Duplicate names are ambiguous across parsers and must not be accepted at
    # an authentication boundary.
    if len({key for key, _value in pairs}) != len(pairs):
        return None
    params = dict(pairs)
    received_hash = params.pop("hash", None)
    if not received_hash or len(received_hash) != 64:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    try:
        auth_date = int(params.get("auth_date", "0"))
    except (TypeError, ValueError):
        return None
    age_seconds = (time.time() if now is None else now) - auth_date
    if (
        auth_date <= 0
        or age_seconds < -INIT_DATA_MAX_FUTURE_SKEW_SECONDS
        or age_seconds > INIT_DATA_MAX_AGE_SECONDS
    ):
        return None
    return params
