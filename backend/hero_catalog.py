"""Server-side view of the checked-in Dota hero id/name/slug catalog."""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path


logger = logging.getLogger(__name__)

_SOURCE = Path(__file__).resolve().parent.parent / "hero-images.js"
_STRING = r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"


def _object_body(source: str, variable: str) -> str:
    match = re.search(
        rf"window\.{re.escape(variable)}\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        source,
        re.DOTALL,
    )
    return match.group("body") if match else ""


def _load_catalog() -> tuple[dict[int, str], dict[int, str]]:
    try:
        source = _SOURCE.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("[hero_catalog] cannot read hero-images.js: %s", exc)
        return {}, {}

    name_to_slug: dict[str, str] = {}
    image_body = _object_body(source, "dotaHeroImages")
    for match in re.finditer(
        rf"(?P<name>{_STRING})\s*:\s*(?P<slug>{_STRING})",
        image_body,
    ):
        try:
            name_to_slug[ast.literal_eval(match.group("name"))] = ast.literal_eval(
                match.group("slug")
            )
        except (SyntaxError, ValueError):
            continue

    id_to_name: dict[int, str] = {}
    id_body = _object_body(source, "dotaHeroIds")
    for match in re.finditer(rf"(?P<name>{_STRING})\s*:\s*(?P<id>\d+)", id_body):
        try:
            name = ast.literal_eval(match.group("name"))
            hero_id = int(match.group("id"))
        except (SyntaxError, ValueError):
            continue
        id_to_name.setdefault(hero_id, name)

    id_to_slug = {
        hero_id: name_to_slug[name]
        for hero_id, name in id_to_name.items()
        if name in name_to_slug
    }
    if len(id_to_name) < 120 or len(id_to_slug) < 120:
        logger.error(
            "[hero_catalog] catalog is unexpectedly small: names=%s slugs=%s",
            len(id_to_name),
            len(id_to_slug),
        )
        return {}, {}
    return id_to_name, id_to_slug


HERO_ID_TO_NAME, HERO_ID_TO_SLUG = _load_catalog()


def hero_identity(hero_id: int) -> tuple[str, str]:
    """Return ``(slug, display_name)`` with a safe fallback for unknown ids."""
    try:
        normalized_id = int(hero_id)
    except (TypeError, ValueError):
        return "", "Unknown hero"
    return (
        HERO_ID_TO_SLUG.get(normalized_id, ""),
        HERO_ID_TO_NAME.get(normalized_id, f"Hero #{normalized_id}"),
    )
