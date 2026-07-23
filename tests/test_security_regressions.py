from __future__ import annotations

import asyncio
import ast
import hashlib
import hmac
import importlib
import importlib.util
import io
import json
import logging
import os
import re
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

from PIL import Image

try:
    import sqlalchemy as sa
except ImportError:  # Minimal local test runtime; production installs requirements.txt.
    sa = None

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

from backend.avatar_store import (
    AvatarValidationError,
    avatar_path,
    public_avatar_url,
    store_avatar_bytes,
)
from backend.security_logging import configure_secure_logging, redact_text
from backend.telegram_auth import validate_telegram_init_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _signed_init_data(bot_token: str, user_id: int, auth_date: int) -> str:
    params = {
        "auth_date": str(auth_date),
        "query_id": "test-query",
        "user": json.dumps(
            {"id": user_id, "first_name": "Test", "username": "tester"},
            separators=(",", ":"),
        ),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


class TelegramAuthTests(unittest.TestCase):
    def test_valid_signature_and_replay_bounds(self):
        now = int(time.time())
        token = "123456:TEST_ONLY_TOKEN"
        payload = _signed_init_data(token, 42, now)
        self.assertEqual(validate_telegram_init_data(payload, token, now=now)["auth_date"], str(now))
        self.assertIsNone(validate_telegram_init_data(payload, token + "x", now=now))
        self.assertIsNone(
            validate_telegram_init_data(_signed_init_data(token, 42, now - 301), token, now=now)
        )
        self.assertIsNone(
            validate_telegram_init_data(_signed_init_data(token, 42, now + 61), token, now=now)
        )

    def test_duplicate_parameters_are_rejected(self):
        now = int(time.time())
        payload = _signed_init_data("123:test", 42, now)
        self.assertIsNone(validate_telegram_init_data(payload + "&auth_date=1", "123:test", now=now))


class AvatarStoreTests(unittest.TestCase):
    def test_image_is_normalized_and_opaque(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ,
            {
                "AVATAR_STORAGE_DIR": temp_dir,
                "MINI_APP_URL": "https://example.test/staging/index.html",
            },
        ):
            source = io.BytesIO()
            Image.new("RGB", (900, 600), (20, 40, 60)).save(source, format="JPEG")
            key = store_avatar_bytes(source.getvalue())
            path = avatar_path(key)
            self.assertIsNotNone(path)
            self.assertNotIn("42", key)
            with Image.open(path) as stored:
                self.assertEqual(stored.format, "WEBP")
                self.assertLessEqual(max(stored.size), 512)
            self.assertEqual(
                public_avatar_url({"avatar_key": key}),
                f"https://example.test/staging/api/avatars/{key}",
            )
            self.assertIsNone(avatar_path("../secret"))

    def test_non_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"AVATAR_STORAGE_DIR": temp_dir}
        ):
            with self.assertRaises(AvatarValidationError):
                store_avatar_bytes(b"<svg><script>alert(1)</script></svg>")


@unittest.skipUnless(importlib.util.find_spec("httpx"), "httpx unavailable")
class HeroPortraitCacheTests(unittest.TestCase):
    def test_frontend_map_is_the_closed_server_allowlist(self):
        from backend import hero_portraits

        source = (PROJECT_ROOT / "hero-images.js").read_text(encoding="utf-8")
        mapped = frozenset(
            re.findall(
                r"^\s*['\"].+['\"]\s*:\s*'([a-z0-9][a-z0-9_-]{0,63})'"
                r"\s*,?(?:\s*//.*)?$",
                source,
                re.MULTILINE,
            )
        )
        self.assertGreaterEqual(len(mapped), 100)
        self.assertEqual(hero_portraits.HERO_SLUGS, mapped)
        self.assertIn("largo", hero_portraits.HERO_SLUGS)
        self.assertIn("obsidian_destroyer", hero_portraits.HERO_SLUGS)
        self.assertTrue(hero_portraits._UPSTREAM.startswith("https://cdn.steamstatic.com/"))

    def test_portraits_are_normalized_cached_and_path_safe(self):
        from backend import hero_portraits

        raw = io.BytesIO()
        Image.new("RGB", (256, 144), (30, 40, 50)).save(raw, format="PNG")
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            hero_portraits, "_CACHE_DIR", Path(temp_dir)
        ), patch.object(
            hero_portraits, "_download_source", return_value=raw.getvalue()
        ) as download:
            (Path(temp_dir) / "axe.png").write_bytes(b"invalid legacy image")
            path = hero_portraits.get_hero_portrait_path("axe")
            self.assertIsNotNone(path)
            self.assertEqual(path.parent, Path(temp_dir))
            self.assertEqual(path.suffix, ".webp")
            with Image.open(path) as cached:
                self.assertEqual(cached.format, "WEBP")
                self.assertEqual(cached.size, (256, 144))
            self.assertEqual(hero_portraits.get_hero_portrait_path("axe"), path)
            download.assert_called_once_with("axe")
            self.assertIsNone(hero_portraits.get_hero_portrait_path("../../etc/passwd"))
            self.assertIsNone(hero_portraits.get_hero_portrait_path("not_a_dota_hero"))


@unittest.skipUnless(importlib.util.find_spec("httpx"), "httpx unavailable")
class AbilityIconCacheTests(unittest.TestCase):
    def test_build_dataset_is_the_closed_server_allowlist(self):
        from backend import ability_icons

        self.assertGreaterEqual(len(ability_icons.ABILITY_NAMES), 300)
        self.assertIn("spirit_breaker_charge_of_darkness", ability_icons.ABILITY_NAMES)
        self.assertIn("shredder_timber_chain", ability_icons.ABILITY_NAMES)
        self.assertNotIn("unknown", ability_icons.ABILITY_NAMES)
        self.assertTrue(ability_icons._UPSTREAM.startswith("https://cdn.steamstatic.com/"))
        self.assertGreaterEqual(ability_icons._MAX_SOURCE_BYTES, 1_165_014)
        self.assertLess(ability_icons._MAX_CACHE_BYTES, ability_icons._MAX_SOURCE_BYTES)

    def test_icons_are_normalized_cached_and_path_safe(self):
        from backend import ability_icons

        raw = io.BytesIO()
        Image.new("RGB", (128, 128), (70, 80, 90)).save(raw, format="PNG")
        ability_name = "spirit_breaker_charge_of_darkness"
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            ability_icons, "_CACHE_DIR", Path(temp_dir)
        ), patch.object(
            ability_icons, "_download_source", return_value=raw.getvalue()
        ) as download:
            path = ability_icons.get_ability_icon_path(ability_name)
            self.assertIsNotNone(path)
            self.assertEqual(path.parent, Path(temp_dir))
            self.assertEqual(path.suffix, ".webp")
            with Image.open(path) as cached:
                self.assertEqual(cached.format, "WEBP")
                self.assertEqual(cached.size, (128, 128))
            self.assertEqual(ability_icons.get_ability_icon_path(ability_name), path)
            download.assert_called_once_with(ability_name)
            self.assertIsNone(ability_icons.get_ability_icon_path("../../etc/passwd"))
            self.assertIsNone(ability_icons.get_ability_icon_path("unknown_ability"))


class HeroCatalogTests(unittest.TestCase):
    def test_share_card_catalog_resolves_names_and_portrait_slugs(self):
        from backend.hero_catalog import hero_identity

        self.assertEqual(hero_identity(3), ("bane", "Bane"))
        self.assertEqual(hero_identity(97), ("magnataur", "Magnus"))
        self.assertEqual(hero_identity(98), ("shredder", "Timbersaw"))


class LoggingTests(unittest.TestCase):
    def test_credentials_are_redacted(self):
        canary = "BOT_TOKEN_CANARY_ABCDEFGHIJKLMNOPQRSTUVWXYZ_secret"
        value = (
            f"GET https://api.telegram.org/file/bot{canary}/photos/a.jpg?token=user-secret&api_key=api-secret "
            "Authorization: Bearer bearer-secret "
            "postgresql://dbuser:dbpass@localhost/app"
        )
        clean = redact_text(value, (canary,))
        for secret in (canary, "user-secret", "api-secret", "bearer-secret", "dbpass"):
            self.assertNotIn(secret, clean)

    def test_uvicorn_access_records_are_filtered(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addHandler(handler)
        old_level = access_logger.level
        access_logger.setLevel(logging.INFO)
        try:
            configure_secure_logging()
            access_logger.info('GET /api/profile_full?token=session-canary HTTP/1.1')
        finally:
            access_logger.removeHandler(handler)
            access_logger.setLevel(old_level)
        self.assertNotIn("session-canary", stream.getvalue())

    def test_uvicorn_access_formatter_keeps_its_five_arguments(self):
        class FiveArgAccessFormatter(logging.Formatter):
            def format(self, record):
                client, method, path, version, status = record.args
                return f'{client} - "{method} {path} HTTP/{version}" {status}'

        configure_secure_logging()
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(FiveArgAccessFormatter())
        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addHandler(handler)
        old_level = access_logger.level
        access_logger.setLevel(logging.INFO)
        try:
            access_logger.info(
                '%s - "%s %s HTTP/%s" %d',
                "127.0.0.1:1",
                "GET",
                "/api/profile_full?token=session-canary",
                "1.1",
                200,
            )
        finally:
            access_logger.removeHandler(handler)
            access_logger.setLevel(old_level)
        self.assertNotIn("session-canary", stream.getvalue())
        self.assertIn("token=<redacted>", stream.getvalue())

    def test_handlers_installed_after_configuration_are_also_protected(self):
        canary = "999999:POST_CONFIG_HANDLER_CANARY"
        configure_secure_logging(canary)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("late.security.handler")
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        try:
            logger.warning("https://api.telegram.org/bot%s/getMe", canary)
        finally:
            logger.removeHandler(handler)
            logger.propagate = True
        self.assertNotIn(canary, stream.getvalue())
        self.assertIn("<redacted>", stream.getvalue())

    def test_late_handler_tracebacks_are_redacted(self):
        canary = "888888:TRACEBACK_CANARY_SECRET"
        configure_secure_logging(canary)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("late.security.traceback")
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        try:
            try:
                raise RuntimeError(f"request failed for {canary}")
            except RuntimeError:
                logger.exception("telegram request failed")
        finally:
            logger.removeHandler(handler)
            logger.propagate = True
        self.assertNotIn(canary, stream.getvalue())
        self.assertIn("<redacted>", stream.getvalue())


@unittest.skipIf(TestClient is None or sa is None, "FastAPI integration dependencies unavailable")
class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory()
        db_path = Path(cls._temp.name) / "api-security.sqlite"
        cls._env = patch.dict(
            os.environ,
            {
                "BOT_TOKEN": "123456:INTEGRATION_TEST_ONLY",
                "CHECK_CHAT_ID": "-1000000000000",
                "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
                "MINI_APP_URL": "https://mini.example.test/staging/",
                "AVATAR_STORAGE_DIR": str(Path(cls._temp.name) / "avatars"),
            },
        )
        cls._env.start()
        cls.api = importlib.import_module("backend.api")
        cls.client = TestClient(cls.api.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.api.engine.dispose()
        cls._env.stop()
        cls._temp.cleanup()

    def test_authorization_header_and_hashed_token_storage(self):
        raw_token = self.api.create_token_for_user(9001)
        response = self.client.get(
            "/api/profile_full", headers={"Authorization": f"Bearer {raw_token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        from backend.models import Token
        with self.api.SessionLocal() as session:
            stored = session.query(Token).filter_by(user_id=9001).one()
            self.assertNotEqual(stored.token, raw_token)
            self.assertEqual(len(stored.token), 64)

    def test_query_string_credentials_are_rejected(self):
        raw_token = self.api.create_token_for_user(9005)
        response = self.client.get(f"/api/profile_full?token={raw_token}")
        self.assertEqual(response.status_code, 400)

    def test_docs_are_not_public(self):
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)

    def test_ability_icons_are_served_from_the_same_origin(self):
        icon_path = Path(self._temp.name) / "ability.webp"
        Image.new("RGB", (64, 64), (10, 20, 30)).save(icon_path, format="WEBP")
        with patch.object(self.api, "get_ability_icon_path", return_value=icon_path):
            response = self.client.get(
                "/api/ability-icons/spirit_breaker_charge_of_darkness.webp"
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "image/webp")
        self.assertIn("immutable", response.headers["cache-control"])

    def test_init_data_is_single_use_and_sessions_are_capped(self):
        now = int(time.time())
        init_data = _signed_init_data(os.environ["BOT_TOKEN"], 9006, now)
        with patch.object(
            self.api,
            "_has_required_subscriptions",
            new=AsyncMock(return_value=True),
        ):
            first = self.client.post("/api/refresh_token", json={"init_data": init_data})
            self.assertEqual(first.status_code, 200)
            replay = self.client.post("/api/refresh_token", json={"init_data": init_data})
            self.assertEqual(replay.status_code, 409)

        from backend.models import Token
        for _ in range(8):
            self.api.create_token_for_user(9007)
        with self.api.SessionLocal() as session:
            self.assertLessEqual(session.query(Token).filter_by(user_id=9007).count(), 5)

    def test_refresh_token_requires_both_channel_subscriptions(self):
        now = int(time.time())
        init_data = _signed_init_data(os.environ["BOT_TOKEN"], 9008, now)
        with patch.object(
            self.api,
            "_has_required_subscriptions",
            new=AsyncMock(return_value=False),
        ):
            denied = self.client.post("/api/refresh_token", json={"init_data": init_data})
        self.assertEqual(denied.status_code, 403)

        from backend.models import Token
        with self.api.SessionLocal() as session:
            self.assertEqual(session.query(Token).filter_by(user_id=9008).count(), 0)

        # A denied attempt must not consume the one-time initData: after the
        # user subscribes, the same fresh Telegram launch can still sign in.
        with patch.object(
            self.api,
            "_has_required_subscriptions",
            new=AsyncMock(return_value=True),
        ):
            allowed = self.client.post("/api/refresh_token", json={"init_data": init_data})
        self.assertEqual(allowed.status_code, 200)

    def test_subscription_check_requires_main_and_sponsor_channels(self):
        calls = []
        sponsor_chat_id = "-1002005211472"
        statuses = iter(["member", "left"])

        class FakeResponse:
            status_code = 200

            def __init__(self, status):
                self._status = status

            def json(self):
                return {"result": {"status": self._status}}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, _url, *, params):
                calls.append(params["chat_id"])
                return FakeResponse(next(statuses))

        with patch.object(self.api, "SPONSOR_CHAT_ID", sponsor_chat_id), \
                patch.object(self.api.httpx, "AsyncClient", return_value=FakeClient()):
            allowed = asyncio.run(self.api._has_required_subscriptions(9009))

        self.assertFalse(allowed)
        self.assertEqual(calls, [self.api.CHECK_CHAT_ID, sponsor_chat_id])

    def test_subscription_check_skips_sponsor_when_not_configured(self):
        calls = []

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"result": {"status": "member"}}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, _url, *, params):
                calls.append(params["chat_id"])
                return FakeResponse()

        with patch.object(self.api, "SPONSOR_CHAT_ID", None), \
                patch.object(self.api.httpx, "AsyncClient", return_value=FakeClient()):
            allowed = asyncio.run(self.api._has_required_subscriptions(9010))

        self.assertTrue(allowed)
        self.assertEqual(calls, [self.api.CHECK_CHAT_ID])

    def test_invalid_init_data_is_rate_limited_before_signature_validation(self):
        with patch.object(self.api, "_enforce_rate") as enforce:
            response = self.client.post(
                "/api/refresh_token", json={"init_data": "not-signed"}
            )
        self.assertEqual(response.status_code, 401)
        enforce.assert_called_once()
        self.assertEqual(enforce.call_args.args[0], "auth_refresh_ip")

        with patch.object(self.api, "_enforce_rate") as invite_enforce:
            invite = self.client.post(
                "/api/battle/invite/bootstrap",
                json={"init_data": "not-signed", "code": "SAFE12"},
            )
        self.assertEqual(invite.status_code, 401)
        invite_enforce.assert_called_once()
        self.assertEqual(
            invite_enforce.call_args.args[0], "battle_invite_bootstrap_ip"
        )

    def test_rate_limit_returns_exact_retry_after_and_api_exposes_it(self):
        from backend import rate_limit

        with patch.object(rate_limit.time, "time", return_value=1_000.0):
            allowed = rate_limit.check_rate_limit(
                "retry_after_test", 9331, limit=1, window_seconds=60
            )
            denied = rate_limit.check_rate_limit(
                "retry_after_test", 9331, limit=1, window_seconds=60
            )
        self.assertEqual(allowed, (True, 1, 0))
        self.assertEqual(denied, (False, 1, 60))

        # Regression: Query.scalar() raises MultipleResultsFound when the
        # limiter contains more than one matching event. Reaching a limit must
        # return a normal denial instead of turning an expected 429 into 500.
        with patch.object(rate_limit.time, "time", return_value=2_000.0):
            first = rate_limit.check_rate_limit(
                "multiple_event_retry_test", 9332, limit=2, window_seconds=60
            )
            second = rate_limit.check_rate_limit(
                "multiple_event_retry_test", 9332, limit=2, window_seconds=60
            )
            multiple_event_denied = rate_limit.check_rate_limit(
                "multiple_event_retry_test", 9332, limit=2, window_seconds=60
            )
        self.assertEqual(first, (True, 1, 0))
        self.assertEqual(second, (True, 2, 0))
        self.assertEqual(multiple_event_denied, (False, 2, 60))

        with patch.object(self.api, "check_rate_limit", return_value=denied):
            with self.assertRaises(self.api.HTTPException) as raised:
                self.api._enforce_rate(
                    "draft_reroll",
                    9331,
                    limit=120,
                    window_seconds=3600,
                    detail="Слишком много обновлений вражеского драфта.",
                )
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers, {"Retry-After": "60"})
        self.assertEqual(
            raised.exception.detail,
            "Слишком много обновлений вражеского драфта.",
        )

        with patch.object(self.api, "check_rate_limit", return_value=(False, 70, 125)):
            with self.assertRaises(self.api.HTTPException) as challenge_raised:
                self.api._enforce_rate(
                    "battle_challenge",
                    9331,
                    limit=70,
                    window_seconds=3600,
                    detail=lambda retry_after: (
                        "Лимит новых вызовов достигнут. Повторно отправьте уже "
                        "созданный вызов или попробуйте через "
                        f"{max(1, (retry_after + 59) // 60)} мин."
                    ),
                )
        self.assertEqual(challenge_raised.exception.status_code, 429)
        self.assertEqual(challenge_raised.exception.headers, {"Retry-After": "125"})
        self.assertEqual(
            challenge_raised.exception.detail,
            "Лимит новых вызовов достигнут. Повторно отправьте уже созданный "
            "вызов или попробуйте через 3 мин.",
        )

    def test_browser_asserted_minigame_score_is_rejected(self):
        raw_token = self.api.create_token_for_user(9201)
        response = self.client.post(
            "/api/minigames/score",
            json={"token": raw_token, "game": "hl_pop", "streak": 100000},
        )
        self.assertEqual(response.status_code, 410)

    def test_minigame_score_is_derived_from_server_run(self):
        raw_token = self.api.create_token_for_user(9202)
        pool = [
            {"id": 1, "matches": 100.0, "kills": 5.0, "deaths": 6.0},
            {"id": 2, "matches": 200.0, "kills": 6.0, "deaths": 7.0},
            {"id": 3, "matches": 300.0, "kills": 7.0, "deaths": 8.0},
        ]
        with patch("backend.stats_db.get_minigame_hl_pool", return_value=pool):
            started = self.client.post(
                "/api/minigames/run/start",
                json={"token": raw_token, "mode": "pop"},
            )
            self.assertEqual(started.status_code, 200, started.text)
            state = started.json()
            restarted = self.client.post(
                "/api/minigames/run/start",
                json={"token": raw_token, "mode": "pop"},
            )
            self.assertEqual(restarted.status_code, 200, restarted.text)
            self.assertEqual(restarted.json()["run_id"], state["run_id"])
            values = {item["id"]: item["matches"] for item in pool}
            ref_value = state["reference"]["value"]
            challenger_value = values[state["challenger"]["id"]]
            guess = "higher" if challenger_value > ref_value else "lower"
            answered = self.client.post(
                "/api/minigames/run/answer",
                json={
                    "token": raw_token,
                    "run_id": state["run_id"],
                    "round": state["round"],
                    "guess": guess,
                },
            )
            self.assertEqual(answered.status_code, 200, answered.text)
            self.assertTrue(answered.json()["correct"])
            self.assertEqual(answered.json()["streak"], 1)
            replay = self.client.post(
                "/api/minigames/run/answer",
                json={
                    "token": raw_token,
                    "run_id": state["run_id"],
                    "round": state["round"],
                    "guess": guess,
                },
            )
            self.assertEqual(replay.status_code, 409)

    def test_minigame_run_is_bound_to_its_owner(self):
        owner_token = self.api.create_token_for_user(9203)
        outsider_token = self.api.create_token_for_user(9204)
        pool = [
            {"id": 1, "matches": 100.0, "kills": 5.0, "deaths": 6.0},
            {"id": 2, "matches": 200.0, "kills": 6.0, "deaths": 7.0},
        ]
        with patch("backend.stats_db.get_minigame_hl_pool", return_value=pool):
            state = self.client.post(
                "/api/minigames/run/start",
                json={"token": owner_token, "mode": "pop"},
            ).json()
            response = self.client.post(
                "/api/minigames/run/answer",
                json={
                    "token": outsider_token,
                    "run_id": state["run_id"],
                    "round": 0,
                    "guess": "higher",
                },
            )
            self.assertEqual(response.status_code, 404)

    def test_hidden_teammate_profile_is_not_enumerable(self):
        from backend.models import TeammateProfile, UserProfile

        viewer_token = self.api.create_token_for_user(9301)
        with self.api.SessionLocal() as session:
            session.add_all([
                UserProfile(user_id=9301, favorite_heroes=[], settings={}),
                UserProfile(user_id=9302, favorite_heroes=[], settings={}),
                TeammateProfile(
                    user_id=9302,
                    rank="Калибровка",
                    hours=0,
                    positions=[1],
                    game_modes=["normal"],
                    microphone=False,
                    discord=False,
                    favorite_heroes=[],
                    about="hidden",
                    status="hidden",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ),
            ])
            session.commit()
        response = self.client.get(
            "/api/teammates/profile/9302",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        self.assertEqual(response.status_code, 404)

    def test_teammate_feed_uses_pseudonymous_ids_and_actions_resolve_them(self):
        from backend.models import TeammateProfile, TeammateRequest, UserProfile

        viewer_token = self.api.create_token_for_user(9311)
        now = datetime.now(timezone.utc)
        with self.api.SessionLocal() as session:
            session.add_all([
                UserProfile(user_id=9311, favorite_heroes=[], settings={}),
                UserProfile(user_id=9312, favorite_heroes=[], settings={"first_name": "Target"}),
                TeammateProfile(
                    user_id=9312, rank="Калибровка", hours=10,
                    positions=[1], game_modes=["normal"], microphone=False,
                    discord=False, favorite_heroes=[], about="", status="ready_now",
                    created_at=now, updated_at=now,
                ),
            ])
            session.commit()
        feed = self.client.get(
            "/api/teammates/feed",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        self.assertEqual(feed.status_code, 200, feed.text)
        public_id = feed.json()["items"][0]["user_id"]
        self.assertNotEqual(public_id, 9312)
        with patch.object(self.api, "_tm_send_bot_message", new=AsyncMock()):
            created = self.client.post(
                "/api/teammates/request",
                json={"token": viewer_token, "to_user_id": public_id},
            )
        self.assertEqual(created.status_code, 200, created.text)
        with self.api.SessionLocal() as session:
            row = session.query(TeammateRequest).filter_by(from_user_id=9311).one()
            self.assertEqual(row.to_user_id, 9312)

    def test_large_data_endpoint_requires_a_valid_session(self):
        self.assertEqual(self.client.get("/api/draft/matchups_all").status_code, 401)
        token = self.api.create_token_for_user(9320)
        with patch.object(self.api, "_load_hero_matchups_bytes", return_value=b"{}"):
            response = self.client.get(
                "/api/draft/matchups_all",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(response.status_code, 200)

    def test_only_single_use_server_draft_challenge_enters_ranking(self):
        from backend.models import DraftResult, UserProfile

        token = self.api.create_token_for_user(9330)
        with self.api.SessionLocal() as session:
            session.add(UserProfile(user_id=9330, favorite_heroes=[], settings={}))
            session.commit()
        with patch.object(self.api, "_enforce_rate") as initial_enforce:
            issued = self.client.get(
                "/api/draft/random",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(issued.status_code, 200, issued.text)
        initial_enforce.assert_any_call(
            "draft_challenge",
            9330,
            limit=120,
            window_seconds=3600,
            detail="Слишком много новых драфтов за короткое время.",
        )
        challenge = issued.json()
        with patch.object(self.api, "_enforce_rate") as enforce:
            repeated = self.client.get(
                "/api/draft/random",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json()["challenge_id"], challenge["challenge_id"])
        self.assertNotIn(
            "draft_challenge",
            [call.args[0] for call in enforce.call_args_list],
        )

        with patch.object(self.api.random, "choice", side_effect=lambda rows: rows[-1]), \
                patch.object(self.api, "_enforce_rate") as enforce:
            rerolled = self.client.get(
                "/api/draft/random?reroll=true",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(rerolled.status_code, 200, rerolled.text)
        self.assertIsNotNone(rerolled.json()["challenge_id"])
        self.assertNotEqual(
            rerolled.json()["challenge_id"], challenge["challenge_id"]
        )
        self.assertTrue(rerolled.json()["ranked"])
        self.assertNotEqual(rerolled.json()["enemy"], challenge["enemy"])
        enforce.assert_any_call(
            "draft_reroll",
            9330,
            limit=120,
            window_seconds=3600,
            detail="Слишком много обновлений вражеского драфта.",
        )
        self.assertEqual(
            sum(call.args[0] == "draft_reroll" for call in enforce.call_args_list),
            1,
        )

        from backend.models import DraftChallenge
        with self.api.SessionLocal() as session:
            replaced = session.get(DraftChallenge, challenge["challenge_id"])
            self.assertIsNone(replaced)

        # Only the newest server-issued challenge remains active and eligible
        # for a ranked leaderboard result.
        still_active = self.client.get(
            "/api/draft/random",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(still_active.status_code, 200, still_active.text)
        self.assertEqual(
            still_active.json()["challenge_id"], rerolled.json()["challenge_id"]
        )

        challenge = rerolled.json()
        enemy_ids = {row["hero_id"] for row in challenge["enemy"]}
        known = [int(k) for k in self.api._load_hero_matchups_file().keys()]
        ally_ids = [hero_id for hero_id in known if hero_id not in enemy_ids][:5]
        ally = [
            {"hero_id": hero_id, "position": f"pos {idx}"}
            for idx, hero_id in enumerate(ally_ids, 1)
        ]
        payload = {
            "token": token,
            "challenge_id": challenge["challenge_id"],
            "ally": ally,
            "enemy": challenge["enemy"],
        }
        first = self.client.post("/api/draft/evaluate", json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["ranked"])
        replay = self.client.post("/api/draft/evaluate", json=payload)
        self.assertEqual(replay.status_code, 409)
        with self.api.SessionLocal() as session:
            self.assertEqual(session.query(DraftResult).filter_by(user_id=9330).count(), 1)

        analysis_payload = dict(payload)
        analysis_payload["challenge_id"] = None
        analysis = self.client.post("/api/draft/evaluate", json=analysis_payload)
        self.assertEqual(analysis.status_code, 200, analysis.text)
        self.assertFalse(analysis.json()["ranked"])
        with self.api.SessionLocal() as session:
            self.assertEqual(session.query(DraftResult).filter_by(user_id=9330).count(), 1)

    def test_opening_analysis_invalidates_the_ranked_draft_server_side(self):
        from backend.models import DraftChallenge, UserProfile

        user_id = 9340
        token = self.api.create_token_for_user(user_id)
        with self.api.SessionLocal() as session:
            session.add(UserProfile(user_id=user_id, favorite_heroes=[], settings={}))
            session.commit()

        issued = self.client.get(
            "/api/draft/random",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(issued.status_code, 200, issued.text)
        old_challenge = issued.json()

        with patch.object(self.api, "_enforce_rate") as enforce:
            invalidated = self.client.post(
                "/api/draft/challenge/invalidate",
                json={"token": token},
            )
            repeated = self.client.post(
                "/api/draft/challenge/invalidate",
                json={"token": token},
            )
        self.assertEqual(invalidated.status_code, 200, invalidated.text)
        self.assertEqual(invalidated.json()["invalidated"], 1)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json()["invalidated"], 0)
        enforce.assert_any_call(
            "draft_reroll",
            user_id,
            limit=120,
            window_seconds=3600,
            detail="Слишком много обновлений вражеского драфта.",
        )
        with self.api.SessionLocal() as session:
            self.assertIsNone(
                session.get(DraftChallenge, old_challenge["challenge_id"])
            )

        enemy_ids = {row["hero_id"] for row in old_challenge["enemy"]}
        known = [int(key) for key in self.api._load_hero_matchups_file().keys()]
        ally_ids = [hero_id for hero_id in known if hero_id not in enemy_ids][:5]
        rejected = self.client.post(
            "/api/draft/evaluate",
            json={
                "token": token,
                "challenge_id": old_challenge["challenge_id"],
                "ally": [
                    {"hero_id": hero_id, "position": f"pos {index}"}
                    for index, hero_id in enumerate(ally_ids, 1)
                ],
                "enemy": old_challenge["enemy"],
            },
        )
        self.assertEqual(rejected.status_code, 404, rejected.text)

        fresh = self.client.get(
            "/api/draft/random",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(fresh.status_code, 200, fresh.text)
        self.assertNotEqual(
            fresh.json()["challenge_id"], old_challenge["challenge_id"]
        )

    def test_authorization_token_is_removed_from_asgi_scope_after_request(self):
        from starlette.requests import Request
        from starlette.responses import Response

        raw_token = self.api.create_token_for_user(9004)
        original_query = b"limit=20"
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/profile_full",
            "raw_path": b"/api/profile_full",
            "query_string": original_query,
            "headers": [(b"authorization", f"Bearer {raw_token}".encode("ascii"))],
            "scheme": "https",
            "server": ("mini.example.test", 443),
            "client": ("127.0.0.1", 12345),
            "root_path": "",
        }
        request = Request(scope)

        async def call_next(_request):
            self.assertIn(b"token=", scope["query_string"])
            return Response(status_code=200)

        response = asyncio.run(
            self.api.app_token_from_authorization(request, call_next)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(scope["query_string"], original_query)

    def test_signed_profile_cannot_cross_user_boundary(self):
        raw_token = self.api.create_token_for_user(9002)
        now = int(time.time())
        valid = _signed_init_data(os.environ["BOT_TOKEN"], 9002, now)
        response = self.client.post(
            "/api/save_telegram_data", json={"token": raw_token, "init_data": valid}
        )
        self.assertEqual(response.status_code, 200)

        forged_identity = _signed_init_data(os.environ["BOT_TOKEN"], 9003, now)
        response = self.client.post(
            "/api/save_telegram_data",
            json={"token": raw_token, "init_data": forged_identity},
        )
        self.assertEqual(response.status_code, 403)

    def test_cors_is_restricted_to_mini_app_origin(self):
        headers = {
            "Origin": "https://mini.example.test",
            "Access-Control-Request-Method": "GET",
        }
        allowed = self.client.options("/api/meta", headers=headers)
        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "https://mini.example.test",
        )
        denied = self.client.options(
            "/api/meta", headers={**headers, "Origin": "https://evil.example"}
        )
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_battle_state_is_visible_only_to_participants(self):
        from backend.models import DraftBattle, UserProfile

        host_token = self.api.create_token_for_user(9101)
        outsider_token = self.api.create_token_for_user(9102)
        with self.api.SessionLocal() as session:
            session.add(UserProfile(user_id=9101, favorite_heroes=[], settings={}))
            session.add(DraftBattle(
                code="SEC123",
                mode="cm",
                status="waiting",
                host_id=9101,
                is_bot=False,
                is_friendly=True,
            ))
            session.commit()

        outsider = self.client.get(
            "/api/battle/state?code=SEC123",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        self.assertEqual(outsider.status_code, 404)
        participant = self.client.get(
            "/api/battle/state?code=SEC123",
            headers={"Authorization": f"Bearer {host_token}"},
        )
        self.assertEqual(participant.status_code, 200)

    def test_battle_events_subscribes_then_rechecks_before_waiting(self):
        payload = {"changed": True, "version": 8, "code": "RACE88"}
        reads = [
            (None, 8801, 20.0),
            (payload, 8801, 0.0),
        ]

        class Subscription:
            def __init__(self):
                self.wait_called = False
                self.closed = False

            async def wait(self, _timeout):
                self.wait_called = True
                return True

            def close(self):
                self.closed = True

        subscription = Subscription()
        with patch.object(self.api, "get_user_id_by_token", return_value=9101), patch.object(
            self.api, "_enforce_rate"
        ), patch.object(
            self.api, "_bt_poll_read", side_effect=reads
        ) as poll_read, patch.object(
            self.api, "_bt_subscribe", return_value=subscription
        ) as subscribe:
            result = asyncio.run(
                self.api.api_battle_events(token="test-token", code="RACE88", since=7)
            )

        self.assertEqual(result, payload)
        self.assertEqual(poll_read.call_count, 2)
        subscribe.assert_called_once_with(8801)
        self.assertFalse(subscription.wait_called)
        self.assertTrue(subscription.closed)

    def test_battle_change_subscription_keeps_early_signal(self):
        from backend import battle_bus

        async def scenario():
            subscription = battle_bus.subscribe_to_changes(8802)
            try:
                # Сигнал приходит после регистрации, но до await — именно окно
                # старой lost-wakeup гонки endpoint'а.
                battle_bus.fire_local(8802)
                return await subscription.wait(0.05)
            finally:
                subscription.close()
                subscription.close()  # cleanup обязан быть идемпотентным

        self.assertTrue(asyncio.run(scenario()))
        self.assertNotIn(8802, battle_bus._waiters)

    def test_assignment_deadline_has_delivery_grace(self):
        from backend.models import DraftBattle

        now = datetime.now(timezone.utc)
        battle = DraftBattle(
            code="GRACE1",
            mode="cm",
            status="assigning",
            host_id=9101,
            guest_id=9102,
            deadline_at=now,
        )
        before_grace = now + timedelta(
            milliseconds=self.api._BT_ASSIGN_GRACE_MS - 1
        )
        at_grace = now + timedelta(milliseconds=self.api._BT_ASSIGN_GRACE_MS)
        self.assertFalse(self.api._bt_tick_pending(battle, before_grace))
        self.assertTrue(self.api._bt_tick_pending(battle, at_grace))

        self.api._bt_start_assign(battle, now)
        assigned_ms = int((battle.deadline_at - now).total_seconds() * 1000)
        self.assertEqual(assigned_ms, 45_000)

    def test_battle_positions_are_persisted_and_idempotently_confirmed(self):
        from backend.models import DraftBattle, DraftBattleAction, UserProfile

        host_id = 9131
        guest_id = 9132
        host_token = self.api.create_token_for_user(host_id)
        now = datetime.now(timezone.utc)
        host_picks = [1, 2, 3, 4, 5]
        guest_picks = [6, 7, 8, 9, 10]
        expected = {str(hero_id): pos for pos, hero_id in enumerate(
            reversed(host_picks), 1
        )}

        with self.api.SessionLocal() as session:
            session.add_all([
                UserProfile(user_id=host_id, favorite_heroes=[], settings={}),
                UserProfile(user_id=guest_id, favorite_heroes=[], settings={}),
            ])
            battle = DraftBattle(
                code="POS913",
                mode="cm",
                status="assigning",
                host_id=host_id,
                guest_id=guest_id,
                is_bot=False,
                first_pick="host",
                deadline_at=now + timedelta(seconds=45),
                started_at=now,
            )
            session.add(battle)
            session.flush()
            session.add_all([
                DraftBattleAction(
                    battle_id=battle.id,
                    idx=idx,
                    actor=actor,
                    kind="pick",
                    hero_id=hero_id,
                    is_auto=False,
                    created_at=now,
                )
                for idx, (actor, hero_id) in enumerate(
                    [("host", hero_id) for hero_id in host_picks]
                    + [("guest", hero_id) for hero_id in guest_picks]
                )
            ])
            session.commit()

        payload = {
            "token": host_token,
            "code": "POS913",
            "positions": expected,
        }
        first = self.client.post("/api/battle/positions", json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["assign"]["you_submitted"])
        self.assertEqual(first.json()["assign"]["your_positions"], expected)

        # Потерянный HTTP-ответ заставляет клиент повторить тот же POST. Повтор
        # должен быть безопасным и подтвердить уже записанную карту.
        repeated = self.client.post("/api/battle/positions", json=payload)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json()["assign"]["your_positions"], expected)
        with self.api.SessionLocal() as session:
            stored = session.query(DraftBattle).filter_by(code="POS913").one()
            self.assertEqual(stored.host_positions, expected)
            self.assertIsNone(stored.guest_positions)
            self.assertEqual(stored.status, "assigning")

    def test_friend_invite_is_remembered_without_creating_unsubscribed_profile(self):
        from backend.models import BattlePendingInvite, DraftBattle, UserProfile

        now = datetime.now(timezone.utc)
        host_id = 9401
        guest_id = 9402
        with self.api.SessionLocal() as session:
            session.add(UserProfile(
                user_id=host_id,
                favorite_heroes=[],
                settings={"first_name": "Invoker"},
            ))
            session.add(DraftBattle(
                code="INV940",
                mode="cm",
                status="waiting",
                host_id=host_id,
                is_bot=False,
                is_friendly=True,
                created_at=now,
            ))
            session.commit()

        init_data = _signed_init_data(
            os.environ["BOT_TOKEN"], guest_id, int(time.time())
        )
        with patch.object(
            self.api,
            "_has_required_subscriptions",
            new=AsyncMock(return_value=False),
        ):
            opened = self.client.post(
                "/api/battle/invite/bootstrap",
                json={"init_data": init_data, "code": "inv940"},
            )
            restored = self.client.post(
                "/api/battle/invite/bootstrap",
                json={"init_data": init_data},
            )

        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertEqual(opened.json()["state"], "pending")
        self.assertFalse(opened.json()["subscribed"])
        self.assertEqual(opened.json()["inviter"]["name"], "Invoker")
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["code"], "INV940")
        with self.api.SessionLocal() as session:
            pending = session.get(BattlePendingInvite, guest_id)
            self.assertIsNotNone(pending)
            self.assertIsNone(pending.subscription_verified_at)
            self.assertIsNone(session.get(UserProfile, guest_id))

    def test_friend_join_requires_fresh_subscription_proof_for_exact_invite(self):
        from backend.models import BattlePendingInvite, DraftBattle, UserProfile

        now = datetime.now(timezone.utc)
        host_id = 9411
        guest_id = 9412
        with self.api.SessionLocal() as session:
            session.add_all([
                UserProfile(
                    user_id=host_id,
                    favorite_heroes=[],
                    settings={"first_name": "Host"},
                ),
                # Existing profile/session simulates a returning user trying to
                # bypass the invite subscription screen with direct API calls.
                UserProfile(
                    user_id=guest_id,
                    favorite_heroes=[],
                    settings={"first_name": "Guest"},
                ),
            ])
            session.add(DraftBattle(
                code="INV941",
                mode="cm",
                status="waiting",
                host_id=host_id,
                is_bot=False,
                is_friendly=True,
                created_at=now,
            ))
            session.add(DraftBattle(
                code="OWN941",
                mode="cm",
                status="waiting",
                host_id=guest_id,
                is_bot=False,
                is_friendly=True,
                created_at=now,
            ))
            session.commit()

        init_data = _signed_init_data(
            os.environ["BOT_TOKEN"], guest_id, int(time.time())
        )
        stale_session = self.api.create_token_for_user(guest_id)
        with patch.object(
            self.api,
            "_has_required_subscriptions",
            new=AsyncMock(return_value=False),
        ):
            denied_preview = self.client.post(
                "/api/battle/invite/bootstrap",
                json={"init_data": init_data, "code": "INV941"},
            )
        self.assertEqual(denied_preview.status_code, 200, denied_preview.text)
        self.assertFalse(denied_preview.json()["subscribed"])
        direct_join = self.client.post(
            "/api/battle/join",
            json={"token": stale_session, "code": "INV941"},
        )
        self.assertEqual(direct_join.status_code, 403, direct_join.text)

        with patch.object(
            self.api,
            "_has_required_subscriptions",
            new=AsyncMock(return_value=True),
        ):
            allowed_preview = self.client.post(
                "/api/battle/invite/bootstrap",
                json={"init_data": init_data, "code": "INV941"},
            )
            # Bootstrap validates but deliberately does not consume initData;
            # refresh_token must still be able to issue the normal API session.
            refreshed = self.client.post(
                "/api/refresh_token", json={"init_data": init_data}
            )
        self.assertTrue(allowed_preview.json()["subscribed"])
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        with patch.object(self.api, "_bt_send_friend_accepted_push"), \
                patch.object(self.api, "_bt_log"):
            joined = self.client.post(
                "/api/battle/join",
                json={"token": refreshed.json()["token"], "code": "INV941"},
            )
        self.assertEqual(joined.status_code, 200, joined.text)
        self.assertEqual(joined.json()["status"], "drafting")
        with self.api.SessionLocal() as session:
            battle = session.query(DraftBattle).filter_by(code="INV941").one()
            self.assertEqual(battle.guest_id, guest_id)
            own_invite = session.query(DraftBattle).filter_by(code="OWN941").one()
            self.assertEqual(own_invite.status, "abandoned")
            self.assertIsNone(session.get(BattlePendingInvite, guest_id))
        active = self.client.get(
            "/api/battle/active",
            headers={"Authorization": f"Bearer {refreshed.json()['token']}"},
        )
        self.assertEqual(active.status_code, 200, active.text)
        self.assertEqual(active.json()["code"], "INV941")
        self.assertEqual(active.json()["status"], "drafting")

    def test_host_can_resume_waiting_friend_invite(self):
        from backend.models import DraftBattle, UserProfile

        host_id = 9421
        token = self.api.create_token_for_user(host_id)
        with self.api.SessionLocal() as session:
            session.add(UserProfile(
                user_id=host_id, favorite_heroes=[], settings={"first_name": "Host"}
            ))
            session.add(DraftBattle(
                code="INV942",
                mode="cm",
                status="waiting",
                host_id=host_id,
                is_bot=False,
                is_friendly=True,
                created_at=datetime.now(timezone.utc),
            ))
            session.commit()
        with patch.object(
            self.api,
            "_bt_invite_url",
            return_value="https://t.me/test_bot?start=db_INV942",
        ):
            response = self.client.get(
                "/api/battle/active",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "waiting")
        self.assertTrue(response.json()["friendly"])
        self.assertEqual(
            response.json()["invite_url"],
            "https://t.me/test_bot?start=db_INV942",
        )

    def test_pair_rating_limit_allows_twenty_battles_then_blocks_the_next(self):
        from backend.models import DraftBattle, UserProfile

        now = datetime.now(timezone.utc)
        with self.api.SessionLocal() as session:
            host = UserProfile(
                user_id=9901, favorite_heroes=[], settings={},
                battle_rating=1200, battle_games_played=0,
            )
            guest = UserProfile(
                user_id=9902, favorite_heroes=[], settings={},
                battle_rating=1200, battle_games_played=0,
            )
            session.add_all([host, guest])
            # Nineteen previous meetings: the twentieth battle is still rated.
            for index in range(19):
                session.add(DraftBattle(
                    code=f"PAIR{index}", mode="cm", status="finished",
                    host_id=9901, guest_id=9902, is_bot=False,
                    is_friendly=False, winner="host", result={"final": {}},
                    created_at=now, finished_at=now,
                ))
            twentieth = DraftBattle(
                code="PAIR20", mode="cm", status="finished",
                host_id=9901, guest_id=9902, is_bot=False,
                is_friendly=False, winner="host", result={"final": {}},
                created_at=now, finished_at=now,
            )
            session.add(twentieth)
            session.flush()
            self.api._bt_apply_ratings(session, twentieth)
            self.assertGreater(twentieth.host_rating_after, twentieth.host_rating_before)
            self.assertLess(twentieth.guest_rating_after, twentieth.guest_rating_before)

            twenty_first = DraftBattle(
                code="PAIR21", mode="cm", status="finished",
                host_id=9901, guest_id=9902, is_bot=False,
                is_friendly=False, winner="host", result={"final": {}},
                created_at=now, finished_at=now,
            )
            session.add(twenty_first)
            session.flush()
            self.api._bt_apply_ratings(session, twenty_first)
            session.commit()
            session.refresh(host)
            session.refresh(guest)
            session.refresh(twentieth)
            session.refresh(twenty_first)
            self.assertEqual(host.battle_rating, twentieth.host_rating_after)
            self.assertEqual(guest.battle_rating, twentieth.guest_rating_after)
            self.assertEqual(host.battle_games_played, 1)
            self.assertEqual(guest.battle_games_played, 1)
            self.assertEqual(
                twenty_first.host_rating_after,
                twenty_first.host_rating_before,
            )
            self.assertEqual(
                twenty_first.guest_rating_after,
                twenty_first.guest_rating_before,
            )

    def test_battle_leaderboard_keeps_pawn_tier_beyond_global_top_2000(self):
        from backend.models import UserProfile

        viewer_id = 120_001
        viewer_token = self.api.create_token_for_user(viewer_id)
        with self.api.SessionLocal() as session:
            profiles = [
                UserProfile(
                    user_id=viewer_id,
                    favorite_heroes=[],
                    settings={"first_name": "Viewer"},
                    battle_rating=1500,
                    battle_games_played=5,
                )
            ]
            profiles.extend(
                UserProfile(
                    user_id=121_000 + index,
                    favorite_heroes=[],
                    settings={"first_name": f"Harbinger {index}"},
                    battle_rating=1000,
                    battle_games_played=5,
                )
                for index in range(2005)
            )
            profiles.extend(
                UserProfile(
                    user_id=124_000 + index,
                    favorite_heroes=[],
                    settings={"first_name": f"Pawn {index}"},
                    battle_rating=999 - index,
                    battle_games_played=5,
                )
                for index in range(3)
            )
            session.add_all(profiles)
            session.commit()

        response = self.client.get(
            "/api/battle/leaderboard",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        pawn_rows = [row for row in payload["top"] if row["rank_key"] == "pawn"]
        self.assertEqual(len(pawn_rows), 3)
        self.assertGreater(pawn_rows[0]["place"], 2000)
        self.assertEqual(payload["total"], 2009)


@unittest.skipIf(sa is None, "SQLAlchemy is not installed in the local test runtime")
class MigrationTests(unittest.TestCase):
    def test_legacy_photo_url_is_purged_on_sqlite(self):
        migration_path = PROJECT_ROOT / "alembic" / "versions" / "0025_purge_unsafe_photo_urls.py"
        spec = importlib.util.spec_from_file_location("migration_0025", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(sa.text(
                "CREATE TABLE user_profiles (user_id INTEGER PRIMARY KEY, settings JSON NOT NULL)"
            ))
            connection.execute(sa.text(
                "CREATE TABLE tokens (token VARCHAR(128) PRIMARY KEY, user_id INTEGER, expires_at DATETIME)"
            ))
            connection.execute(
                sa.text("INSERT INTO user_profiles (user_id, settings) VALUES (1, :settings)"),
                {"settings": json.dumps({"photo_url": "TOKEN_CANARY", "first_name": "A"})},
            )
            connection.execute(sa.text(
                "INSERT INTO tokens (token, user_id, expires_at) VALUES ('raw-session', 1, '2099-01-01')"
            ))

            class _Operations:
                @staticmethod
                def get_bind():
                    return connection

                @staticmethod
                def execute(statement):
                    return connection.execute(statement)

            with patch.object(migration, "op", _Operations):
                migration.upgrade()
            settings = json.loads(connection.execute(
                sa.text("SELECT settings FROM user_profiles WHERE user_id = 1")
            ).scalar_one())
            self.assertEqual(settings, {"first_name": "A"})
            self.assertEqual(
                connection.execute(sa.text("SELECT COUNT(*) FROM tokens")).scalar_one(), 0
            )

    def test_security_hardening_purges_untrusted_minigame_scores(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        migration_path = PROJECT_ROOT / "alembic" / "versions" / "0026_security_hardening.py"
        spec = importlib.util.spec_from_file_location("migration_0026", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(sa.text(
                "CREATE TABLE user_profiles (user_id INTEGER PRIMARY KEY, settings JSON NOT NULL)"
            ))
            connection.execute(sa.text(
                "CREATE TABLE draft_results (id INTEGER PRIMARY KEY, user_id INTEGER, total_score FLOAT)"
            ))
            connection.execute(sa.text(
                "INSERT INTO draft_results (id, user_id, total_score) VALUES (1, 1, 100)"
            ))
            connection.execute(
                sa.text("INSERT INTO user_profiles (user_id, settings) VALUES (1, :settings)"),
                {"settings": json.dumps({"minigame_best": {"hl_pop": 99999}, "first_name": "A"})},
            )
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()
            settings = json.loads(connection.execute(
                sa.text("SELECT settings FROM user_profiles WHERE user_id = 1")
            ).scalar_one())
            self.assertEqual(settings, {"first_name": "A"})
            self.assertIn("minigame_runs", sa.inspect(connection).get_table_names())
            self.assertIn("draft_challenges", sa.inspect(connection).get_table_names())
            minigame_indexes = {
                item["name"] for item in sa.inspect(connection).get_indexes("minigame_runs")
            }
            challenge_indexes = {
                item["name"] for item in sa.inspect(connection).get_indexes("draft_challenges")
            }
            self.assertIn("uq_minigame_runs_active_user_game", minigame_indexes)
            self.assertIn("uq_draft_challenges_unconsumed_user", challenge_indexes)
            self.assertEqual(
                connection.execute(sa.text("SELECT COUNT(*) FROM draft_results")).scalar_one(), 0
            )

    def test_pending_battle_invite_migration_has_membership_proof(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        migration_path = (
            PROJECT_ROOT / "alembic" / "versions" /
            "0027_add_battle_pending_invites.py"
        )
        spec = importlib.util.spec_from_file_location("migration_0027", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(sa.text(
                "CREATE TABLE draft_battles (id INTEGER PRIMARY KEY)"
            ))
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()
            inspector = sa.inspect(connection)
            columns = {
                item["name"]
                for item in inspector.get_columns("battle_pending_invites")
            }
            self.assertIn("subscription_verified_at", columns)
            indexes = {
                item["name"]
                for item in inspector.get_indexes("battle_pending_invites")
            }
            self.assertIn("ix_battle_pending_invites_battle_id", indexes)
            self.assertIn("ix_battle_pending_invites_expires_at", indexes)


class SourceBoundaryTests(unittest.TestCase):
    def test_privileged_bot_handlers_recheck_server_admin_ids(self):
        source = (PROJECT_ROOT / "backend" / "bot.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {
            node.name: ast.get_source_segment(source, node) or ""
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        privileged = {
            "stats_mode_command",
            "admin_feedback_command",
            "admin_users_command",
            "admin_matches_command",
            "tm_stats_command",
            "analytics_command",
            "force_update_builds_command",
            "topdraft_command",
            "ban_command",
            "unban_command",
            "broadcast_receive",
            "broadcast_callback",
            "broadcast_resume_command",
        }
        missing = sorted(
            name for name in privileged if "ADMIN_IDS" not in functions.get(name, "")
        )
        self.assertEqual(missing, [], f"privileged handlers without admin check: {missing}")

    def test_every_mutating_api_route_has_an_authentication_boundary(self):
        source = (PROJECT_ROOT / "backend" / "api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        accepted = {
            "get_user_id_by_token",
            "_tm_require_user",
            "_tm_authenticate",
            "_validate_telegram_init_data",
        }
        missing = []
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            mutation_routes = []
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr in {"post", "put", "patch", "delete"}
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    continue
                mutation_routes.append(str(decorator.args[0].value))
            if not mutation_routes:
                continue
            calls = {
                call.func.id
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            }
            if not calls.intersection(accepted):
                missing.extend(mutation_routes)
        self.assertEqual(missing, [], f"mutation routes without auth: {missing}")

    def test_known_token_leak_paths_do_not_return(self):
        bot_source = (PROJECT_ROOT / "backend" / "bot.py").read_text(encoding="utf-8")
        api_source = (PROJECT_ROOT / "backend" / "api.py").read_text(encoding="utf-8")
        html_source = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        script_source = (PROJECT_ROOT / "script.js").read_text(encoding="utf-8")
        hero_images_source = (PROJECT_ROOT / "hero-images.js").read_text(encoding="utf-8")
        self.assertNotIn("file.file_path", bot_source)
        self.assertNotIn('mini_app_url_with_token = f"{MINI_APP_URL}?token=', bot_source)
        self.assertNotIn("create_token_for_user,", bot_source)
        self.assertNotIn('urlencode({"token": token})', bot_source)
        self.assertIn("drop_pending_updates=True", bot_source)
        self.assertIn("MenuButtonCommands", bot_source)
        self.assertNotIn("MenuButtonWebApp", bot_source)
        self.assertNotIn("ReplyKeyboardMarkup", bot_source)
        self.assertIn("ReplyKeyboardRemove", bot_source)
        self.assertIn('text="Открыть D2Helper",\n            web_app=WebAppInfo(url=mini_app_url)', bot_source)
        self.assertIn("role = _bt_require_role(battle, uid)", api_source)
        self.assertIn("role = _bt_require_role(battle, user_id)", api_source)
        self.assertIn("token=_token_digest(token_str)", (PROJECT_ROOT / "backend" / "db.py").read_text(encoding="utf-8"))
        self.assertIn('script.js?v=323', html_source)
        self.assertIn('styles.css?v=256', html_source)
        self.assertNotIn("frozenset({556944111})", bot_source)
        self.assertNotIn("traceback.print_exc()", bot_source)
        self.assertIn("client-supplied scores are not accepted", api_source)
        self.assertIn("function discardTokenFromUrl()", script_source)
        self.assertNotIn("function getTokenFromUrl()", script_source)
        self.assertIn("_BT_RATED_PAIR_LIMIT_24H = 20", api_source)
        self.assertGreaterEqual(api_source.count("_bt_lock_user(db, uid)"), 3)
        self.assertIn("with_for_update()", api_source)
        self.assertIn("/hero-images/${slug}.webp", hero_images_source)
        self.assertNotIn("return `https://cdn.cloudflare", hero_images_source)
        self.assertIn('hero-images.js?v=2', html_source)
        self.assertIn("/ability-icons/", script_source)
        self.assertNotIn("dota_react/abilities/", script_source)
        self.assertIn("hero_identity(run.reference_id)", api_source)
        self.assertIn("hero_identity(run.challenger_id)", api_source)
        self.assertIn("resp.headers.get('Retry-After')", script_source)
        self.assertIn("/draft/challenge/invalidate", api_source)
        self.assertIn("/draft/challenge/invalidate", script_source)
        self.assertIn("loadGeneration !== _drafterLoadGeneration", script_source)
        self.assertIn("Лимит обновлений достигнут", script_source)
        self.assertIn("limit=120", api_source)
        self.assertIn("SPONSOR_CHANNEL_URL", bot_source)
        self.assertNotIn("https://t.me/+NtPbXaoKbeo2YjEy", bot_source)
        self.assertEqual(bot_source.count("await _reply_subscription_gate("), 6)
        battle_branch = bot_source.index(
            'if _start_payload and _start_payload.startswith("db_"):'
        )
        avatar_fetch = bot_source.index('avatar_state = "error"')
        self.assertLess(battle_branch, avatar_fetch)
        self.assertIn('"Открыть вызов"', bot_source[battle_branch:avatar_fetch])
        self.assertNotIn("_PENDING_BATTLE_INVITES", bot_source)
        self.assertIn("/battle/invite/bootstrap", script_source)
        self.assertIn("['waiting', 'searching', 'drafting', 'assigning']", script_source)
        self.assertIn("_btSubmitPositionsReliable", script_source)
        self.assertIn("submitted && submitted[role] === true", script_source)
        self.assertIn("_btAckPositions(_bt.state, positions)", script_source)
        self.assertIn("Расстановка принята сервером", script_source)
        self.assertIn("Сервер использовал порядок пиков", script_source)
        self.assertIn("subscribe_to_changes as _bt_subscribe", api_source)
        self.assertIn("_BT_ASSIGN_GRACE_MS = 3_000", api_source)


if __name__ == "__main__":
    unittest.main()
