"""Validated same-origin cache for public Dota hero portraits."""

from __future__ import annotations

import io
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
    os.environ.get("HERO_PORTRAIT_CACHE_DIR", _ROOT / "assets" / "hero_portraits")
)
_SOURCE_MAP = _ROOT / "hero-images.js"
_UPSTREAM = (
    "https://cdn.steamstatic.com/apps/dota2/images/"
    "dota_react/heroes/{slug}.png"
)
_MAX_SOURCE_BYTES = 512 * 1024
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MAP_LINE_RE = re.compile(
    r"^\s*['\"].+['\"]\s*:\s*'([a-z0-9][a-z0-9_-]{0,63})'"
    r"\s*,?(?:\s*//.*)?$"
)


def _load_allowed_slugs() -> frozenset[str]:
    """Load the frontend's checked-in hero map as a closed allowlist."""
    try:
        slugs = {
            match.group(1)
            for line in _SOURCE_MAP.read_text(encoding="utf-8").splitlines()
            if (match := _MAP_LINE_RE.match(line))
        }
    except OSError as exc:
        logger.error("[hero_portraits] cannot read hero map: %s", exc)
        return frozenset()
    if len(slugs) < 100:
        logger.error("[hero_portraits] hero allowlist is unexpectedly small: %s", len(slugs))
        return frozenset()
    return frozenset(slugs)


HERO_SLUGS = _load_allowed_slugs()

_locks_guard = threading.Lock()
_slug_locks: dict[str, threading.Lock] = {}


def _slug_lock(slug: str) -> threading.Lock:
    with _locks_guard:
        return _slug_locks.setdefault(slug, threading.Lock())


def _normalized_webp(raw: bytes) -> bytes:
    if not raw or len(raw) > _MAX_SOURCE_BYTES:
        raise ValueError("hero portrait has invalid size")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            width, height = source.size
            if not (64 <= width <= 1024 and 64 <= height <= 1024):
                raise ValueError("hero portrait has invalid dimensions")
            source.load()
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("hero portrait is not a valid image") from exc

    output = io.BytesIO()
    image.save(output, format="WEBP", quality=88, method=4)
    encoded = output.getvalue()
    if not encoded or len(encoded) > _MAX_SOURCE_BYTES:
        raise ValueError("hero portrait encoding failed")
    return encoded


def _download_source(slug: str) -> bytes:
    url = _UPSTREAM.format(slug=slug)
    chunks: list[bytes] = []
    total = 0
    with httpx.stream(
        "GET",
        url,
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


def get_hero_portrait_path(slug: str) -> Path | None:
    """Return a normalized cached portrait, downloading only allowlisted slugs."""
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug) or slug not in HERO_SLUGS:
        return None

    target = _CACHE_DIR / f"{slug}.webp"
    if _is_usable_cache_file(target):
        return target

    with _slug_lock(slug):
        if _is_usable_cache_file(target):
            return target
        try:
            legacy_png = _CACHE_DIR / f"{slug}.png"
            encoded: bytes | None = None
            if _is_usable_cache_file(legacy_png):
                try:
                    encoded = _normalized_webp(legacy_png.read_bytes())
                except (OSError, ValueError):
                    logger.warning(
                        "[hero_portraits] ignoring invalid legacy cache for %s", slug
                    )
            if encoded is None:
                encoded = _normalized_webp(_download_source(slug))
            _write_atomic(target, encoded)
            return target
        except (OSError, ValueError, httpx.HTTPError) as exc:
            logger.warning("[hero_portraits] fetch failed for %s: %s", slug, exc)
            return None


def prewarm_all(*, workers: int = 8) -> list[str]:
    """Fill the bounded portrait cache and return the slugs that failed."""
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 16))) as pool:
        futures = {pool.submit(get_hero_portrait_path, slug): slug for slug in HERO_SLUGS}
        for future in as_completed(futures):
            slug = futures[future]
            try:
                if future.result() is None:
                    failures.append(slug)
            except Exception:
                logger.exception("[hero_portraits] unexpected prewarm failure for %s", slug)
                failures.append(slug)
    return sorted(failures)


if __name__ == "__main__":
    missing = prewarm_all()
    print(f"hero_portraits_total={len(HERO_SLUGS)}")
    print(f"hero_portraits_failed={len(missing)}")
    if missing:
        print("failed_slugs=" + ",".join(missing))
        raise SystemExit(1)
