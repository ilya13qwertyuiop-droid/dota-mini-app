"""Secure local storage for Telegram profile avatars.

Telegram file download URLs contain the bot token and must never be persisted
or returned to a browser.  This module stores only validated image bytes under
an opaque random key and builds a first-party URL for API responses.
"""

from __future__ import annotations

import os
import re
import secrets
import tempfile
import warnings
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from PIL import Image, ImageOps, UnidentifiedImageError


AVATAR_MAX_SOURCE_BYTES = 5 * 1024 * 1024
AVATAR_MAX_PIXELS = 16_000_000
AVATAR_MAX_EDGE = 512
_AVATAR_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")
_ALLOWED_SOURCE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


class AvatarValidationError(ValueError):
    """Raised when downloaded bytes are not a safe supported image."""


def avatar_storage_dir() -> Path:
    """Return the private avatar cache directory.

    Production should set ``AVATAR_STORAGE_DIR`` to a directory outside the
    nginx document root.  The project-local fallback is intentionally hidden,
    ignored by Git and useful for development/staging setup.
    """

    configured = os.environ.get("AVATAR_STORAGE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent / ".runtime" / "avatars").resolve()


def is_valid_avatar_key(key: object) -> bool:
    return isinstance(key, str) and _AVATAR_KEY_RE.fullmatch(key) is not None


def avatar_path(key: object) -> Path | None:
    """Resolve an opaque key to a cached file without permitting traversal."""

    if not is_valid_avatar_key(key):
        return None
    root = avatar_storage_dir()
    candidate = (root / f"{key}.webp").resolve()
    if candidate.parent != root or not candidate.is_file():
        return None
    return candidate


def delete_avatar(key: object) -> None:
    path = avatar_path(key)
    if path is not None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def store_avatar_bytes(data: bytes | bytearray, previous_key: object = None) -> str:
    """Validate, normalize and atomically store a Telegram avatar.

    Only decoded JPEG/PNG/WEBP input is accepted.  The output is always a
    metadata-free WebP with a random 192-bit lookup key.  A previous cached
    image is deleted only after the new file has been committed successfully.
    """

    raw = bytes(data)
    if not raw or len(raw) > AVATAR_MAX_SOURCE_BYTES:
        raise AvatarValidationError("avatar source size is invalid")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if (source.format or "").upper() not in _ALLOWED_SOURCE_FORMATS:
                    raise AvatarValidationError("unsupported avatar format")
                width, height = source.size
                if width <= 0 or height <= 0 or width * height > AVATAR_MAX_PIXELS:
                    raise AvatarValidationError("avatar dimensions are invalid")
                source.load()
                normalized = ImageOps.exif_transpose(source)
                has_alpha = normalized.mode in ("RGBA", "LA") or (
                    normalized.mode == "P" and "transparency" in normalized.info
                )
                normalized = normalized.convert("RGBA" if has_alpha else "RGB")
                normalized.thumbnail(
                    (AVATAR_MAX_EDGE, AVATAR_MAX_EDGE), Image.Resampling.LANCZOS
                )
    except AvatarValidationError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as exc:
        raise AvatarValidationError("avatar is not a valid image") from exc

    root = avatar_storage_dir()
    root.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(24)
    destination = root / f"{key}.webp"
    fd, temp_name = tempfile.mkstemp(prefix=".avatar-", suffix=".tmp", dir=root)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        normalized.save(temp_path, format="WEBP", quality=84, method=6)
        try:
            temp_path.chmod(0o600)
        except OSError:
            pass
        os.replace(temp_path, destination)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    if is_valid_avatar_key(previous_key) and previous_key != key:
        delete_avatar(previous_key)
    return key


def public_avatar_url(settings: dict | None) -> str | None:
    """Build a first-party avatar URL from sanitized profile settings."""

    key = (settings or {}).get("avatar_key")
    if not is_valid_avatar_key(key):
        return None

    mini_app_url = os.environ.get("MINI_APP_URL", "").strip()
    if mini_app_url:
        parsed = urlsplit(mini_app_url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            path = parsed.path.rstrip("/")
            if path.endswith("/index.html"):
                path = path[: -len("/index.html")]
            api_path = f"{path}/api/avatars/{key}" if path else f"/api/avatars/{key}"
            return urlunsplit((parsed.scheme, parsed.netloc, api_path, "", ""))
    return f"/api/avatars/{key}"
