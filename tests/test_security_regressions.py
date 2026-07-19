from __future__ import annotations

import hashlib
import hmac
import importlib
import importlib.util
import io
import json
import logging
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
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
            validate_telegram_init_data(_signed_init_data(token, 42, now - 601), token, now=now)
        )
        self.assertIsNone(
            validate_telegram_init_data(_signed_init_data(token, 42, now + 301), token, now=now)
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


class SourceBoundaryTests(unittest.TestCase):
    def test_known_token_leak_paths_do_not_return(self):
        bot_source = (PROJECT_ROOT / "backend" / "bot.py").read_text(encoding="utf-8")
        api_source = (PROJECT_ROOT / "backend" / "api.py").read_text(encoding="utf-8")
        html_source = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("file.file_path", bot_source)
        self.assertNotIn('mini_app_url_with_token = f"{MINI_APP_URL}?token=', bot_source)
        self.assertIn("role = _bt_require_role(battle, uid)", api_source)
        self.assertIn("role = _bt_require_role(battle, user_id)", api_source)
        self.assertIn("token=_token_digest(token_str)", (PROJECT_ROOT / "backend" / "db.py").read_text(encoding="utf-8"))
        self.assertIn('script.js?v=314', html_source)


if __name__ == "__main__":
    unittest.main()
