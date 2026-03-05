"""
news_updater.py — Background worker that polls the Dota 2 Steam RSS feed and
broadcasts new articles to subscribed Telegram users.

Run as a standalone process:
    python -m backend.news_updater          # from project root
    python backend/news_updater.py          # also works

Environment variables:
    BOT_TOKEN                   — Telegram bot token (required)
    DATABASE_URL                — SQLAlchemy DB URL (default: SQLite dev path)
    NEWS_CHECK_INTERVAL_SECONDS — polling interval in seconds (default: 300)
    NEWS_TEST_MODE              — set to "1" to re-send the last 3 RSS items to
                                   a single test user instead of real subscribers
    NEWS_TEST_USER_ID           — Telegram user_id to notify in test mode
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Path bootstrap — allow running as "python backend/news_updater.py"
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
NEWS_CHECK_INTERVAL_SECONDS: int = int(os.getenv("NEWS_CHECK_INTERVAL_SECONDS", "300"))
NEWS_TEST_MODE: bool = os.getenv("NEWS_TEST_MODE", "0") == "1"
NEWS_TEST_USER_ID: int | None = (
    int(os.environ["NEWS_TEST_USER_ID"])
    if os.environ.get("NEWS_TEST_USER_ID")
    else None
)

RSS_URL = "https://steamcommunity.com/games/dota2/rss/"

# Telegram hard limit is ~30 msg/sec across all chats; 0.05 s ≈ 20 msg/sec
_SEND_DELAY = 0.05

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("news_updater")

# ---------------------------------------------------------------------------
# DB helpers (imported lazily to allow path bootstrap above)
# ---------------------------------------------------------------------------

from backend.db import (  # noqa: E402
    get_latest_news_guids,
    get_news_subscribers,
    mark_news_notified,
    news_guid_exists,
    save_dota_news,
)

# ---------------------------------------------------------------------------
# RSS parsing
# ---------------------------------------------------------------------------

def _parse_rss(xml_bytes: bytes) -> list[dict]:
    """Parses Dota 2 RSS feed bytes into a list of item dicts.

    Each dict has: guid, title, link, published_at (datetime | None).
    Returns items in feed order (newest first for Steam RSS).
    """
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []

    items: list[dict] = []
    for item in channel.findall("item"):
        guid_el = item.find("guid")
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")

        guid = (guid_el.text or "").strip() if guid_el is not None else ""
        if not guid:
            continue

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""

        published_at: datetime | None = None
        if pubdate_el is not None and pubdate_el.text:
            try:
                published_at = parsedate_to_datetime(pubdate_el.text.strip())
                # Ensure UTC-aware
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        items.append({"guid": guid, "title": title, "link": link, "published_at": published_at})

    return items


# ---------------------------------------------------------------------------
# Telegram send
# ---------------------------------------------------------------------------

async def _send_message(client: httpx.AsyncClient, user_id: int, text: str) -> bool:
    """Sends a Telegram message via Bot API. Returns True on success."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = await client.post(
            url,
            json={"chat_id": user_id, "text": text, "parse_mode": "MarkdownV2", "disable_web_page_preview": False},
            timeout=10,
        )
        if resp.status_code != 200:
            data = resp.json()
            logger.warning("[send] user=%s status=%s desc=%s", user_id, resp.status_code, data.get("description"))
            return False
        return True
    except Exception as exc:
        logger.warning("[send] user=%s error=%s", user_id, exc)
        return False


_MDV2_SPECIAL = re.compile(r'([_*\[\]()~`>#+\-=|{}.!\\])')


def _escape_mdv2(text: str) -> str:
    """Escapes all MarkdownV2 special characters in plain text."""
    return _MDV2_SPECIAL.sub(r'\\\1', text)


def _format_news(title: str, link: str) -> str:
    """Returns a MarkdownV2-formatted news message."""
    escaped_title = _escape_mdv2(title)
    escaped_link = _escape_mdv2(link)
    return f"🗞 *Новость Dota 2*\n\n*{escaped_title}*\n\n🔗 [Читать]({escaped_link})"


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------

async def _broadcast(client: httpx.AsyncClient, item: dict, user_ids: list[int]) -> None:
    """Sends item to all user_ids, throttled to avoid Telegram rate limit."""
    text = _format_news(item["title"], item["link"])
    ok = err = 0
    for uid in user_ids:
        success = await _send_message(client, uid, text)
        if success:
            ok += 1
        else:
            err += 1
        await asyncio.sleep(_SEND_DELAY)
    logger.info(
        "[broadcast] guid=%s sent=%d err=%d",
        item["guid"][:60], ok, err,
    )
    await asyncio.to_thread(mark_news_notified, item["guid"])


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def _check_and_notify(client: httpx.AsyncClient) -> None:
    """One poll cycle: fetch RSS, find new items, broadcast."""
    logger.info("[poll] fetching RSS %s", RSS_URL)
    try:
        resp = await client.get(RSS_URL, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("[poll] RSS fetch failed: %s", exc)
        return

    items = _parse_rss(resp.content)
    logger.info("[poll] parsed %d items from feed", len(items))

    if NEWS_TEST_MODE:
        await _run_test_mode(client, items)
        return

    # Normal mode: process only unseen guids
    new_items: list[dict] = []
    for item in items:
        if not await asyncio.to_thread(news_guid_exists, item["guid"]):
            await asyncio.to_thread(
                save_dota_news,
                item["guid"], item["title"], item["link"], item["published_at"],
            )
            new_items.append(item)

    if not new_items:
        logger.info("[poll] no new items")
        return

    subscribers = await asyncio.to_thread(get_news_subscribers)
    if not subscribers:
        logger.info("[poll] %d new item(s) but no subscribers", len(new_items))
        # Still mark notified so we don't re-process them next cycle
        for item in new_items:
            await asyncio.to_thread(mark_news_notified, item["guid"])
        return

    logger.info(
        "[poll] broadcasting %d new item(s) to %d subscriber(s)",
        len(new_items), len(subscribers),
    )
    for item in new_items:
        await _broadcast(client, item, subscribers)


async def _run_test_mode(client: httpx.AsyncClient, rss_items: list[dict]) -> None:
    """Test mode: take the most recent RSS item (saving any unseen ones first)
    and send it only to NEWS_TEST_USER_ID.
    """
    if not NEWS_TEST_USER_ID:
        logger.error("[test] NEWS_TEST_MODE=1 but NEWS_TEST_USER_ID is not set — aborting")
        return

    # Save any unseen items so they appear in the DB for get_latest_news_guids()
    for item in rss_items:
        if not await asyncio.to_thread(news_guid_exists, item["guid"]):
            await asyncio.to_thread(
                save_dota_news,
                item["guid"], item["title"], item["link"], item["published_at"],
            )

    # Use the most recent item from DB (covers the case where RSS was already parsed before)
    latest = await asyncio.to_thread(get_latest_news_guids, 1)
    logger.info("[test] sending %d item(s) to user %s", len(latest), NEWS_TEST_USER_ID)

    for item in latest:
        text = _format_news(item["title"], item["link"])
        await _send_message(client, NEWS_TEST_USER_ID, text)
        await asyncio.sleep(_SEND_DELAY)

    logger.info("[test] done — exiting (test mode runs once then stops)")


async def run() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    logger.info(
        "news_updater starting | interval=%ds test_mode=%s",
        NEWS_CHECK_INTERVAL_SECONDS, NEWS_TEST_MODE,
    )

    async with httpx.AsyncClient() as client:
        if NEWS_TEST_MODE:
            # In test mode run once immediately then exit
            await _check_and_notify(client)
            return

        while True:
            try:
                await _check_and_notify(client)
            except Exception as exc:
                logger.error("[loop] unhandled error: %s", exc, exc_info=True)
            await asyncio.sleep(NEWS_CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
