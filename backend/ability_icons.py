"""Validated same-origin cache for Dota ability icons."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from PIL import Image, UnidentifiedImageError


logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_CACHE_DIR = Path(
    os.environ.get("ABILITY_ICON_CACHE_DIR", _ROOT / "assets" / "ability_icons")
)
_SOURCE_DATA = _ROOT / "dota_builds.json"
_UPSTREAM = (
    "https://cdn.steamstatic.com/apps/dota2/images/"
    "dota_react/abilities/{ability_name}.png"
)
_MAX_SOURCE_BYTES = 512 * 1024
_ABILITY_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,95}$")


def _load_allowed_abilities() -> frozenset[str]:
    """Build a closed allowlist from the same dataset used by hero builds."""
    try:
        raw = json.loads(_SOURCE_DATA.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error("[ability_icons] cannot read dota_builds.json: %s", exc)
        return frozenset()

    names: set[str] = set()
    for positions in raw.values():
        if not isinstance(positions, dict):
            continue
        for position in positions.values():
            if not isinstance(position, dict):
                continue
            for ability in position.get("abilities") or []:
                if not isinstance(ability, dict) or ability.get("isTalent"):
                    continue
                name = ability.get("name")
                if (
                    isinstance(name, str)
                    and name != "unknown"
                    and _ABILITY_RE.fullmatch(name)
                ):
                    names.add(name)
    if len(names) < 300:
        logger.error("[ability_icons] ability allowlist is unexpectedly small: %s", len(names))
        return frozenset()
    return frozenset(names)


ABILITY_NAMES = _load_allowed_abilities()

_locks_guard = threading.Lock()
_ability_locks: dict[str, threading.Lock] = {}


def _ability_lock(name: str) -> threading.Lock:
    with _locks_guard:
        return _ability_locks.setdefault(name, threading.Lock())


def _normalized_webp(raw: bytes) -> bytes:
    if not raw or len(raw) > _MAX_SOURCE_BYTES:
        raise ValueError("ability icon has invalid size")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            width, height = source.size
            if not (32 <= width <= 1024 and 32 <= height <= 1024):
                raise ValueError("ability icon has invalid dimensions")
            source.load()
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("ability icon is not a valid image") from exc

    output = io.BytesIO()
    image.save(output, format="WEBP", quality=90, method=4)
    encoded = output.getvalue()
    if not encoded or len(encoded) > _MAX_SOURCE_BYTES:
        raise ValueError("ability icon encoding failed")
    return encoded


def _download_source(ability_name: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    with httpx.stream(
        "GET",
        _UPSTREAM.format(ability_name=ability_name),
        timeout=httpx.Timeout(12.0, connect=4.0),
        follow_redirects=False,
    ) as response:
        response.raise_for_status()
        if not response.headers.get("content-type", "").lower().startswith("image/"):
            raise ValueError("upstream did not return an image")
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > _MAX_SOURCE_BYTES:
                raise ValueError("upstream image is too large")
            chunks.append(chunk)
    return b"".join(chunks)


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _is_usable_cache_file(path: Path) -> bool:
    try:
        return path.is_file() and 0 < path.stat().st_size <= _MAX_SOURCE_BYTES
    except OSError:
        return False


def get_ability_icon_path(ability_name: str) -> Path | None:
    """Return a normalized cached icon for an allowlisted ability."""
    if (
        not isinstance(ability_name, str)
        or not _ABILITY_RE.fullmatch(ability_name)
        or ability_name not in ABILITY_NAMES
    ):
        return None

    target = _CACHE_DIR / f"{ability_name}.webp"
    if _is_usable_cache_file(target):
        return target

    with _ability_lock(ability_name):
        if _is_usable_cache_file(target):
            return target
        try:
            encoded = _normalized_webp(_download_source(ability_name))
            _write_atomic(target, encoded)
            return target
        except (OSError, ValueError, httpx.HTTPError) as exc:
            logger.warning("[ability_icons] fetch failed for %s: %s", ability_name, exc)
            return None


def prewarm_all(*, workers: int = 8) -> list[str]:
    """Fill the bounded ability cache and return the names that failed."""
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 16))) as pool:
        futures = {
            pool.submit(get_ability_icon_path, name): name
            for name in ABILITY_NAMES
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                if future.result() is None:
                    failures.append(name)
            except Exception:
                logger.exception("[ability_icons] unexpected prewarm failure for %s", name)
                failures.append(name)
    return sorted(failures)


if __name__ == "__main__":
    missing = prewarm_all()
    print(f"ability_icons_total={len(ABILITY_NAMES)}")
    print(f"ability_icons_failed={len(missing)}")
    if missing:
        print("failed_abilities=" + ",".join(missing))
        raise SystemExit(1)
