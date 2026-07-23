"""
stats_updater.py — воркер фэнтези-статистики про-игроков (TI Compendium).

ПОЛНОСТЬЮ ПЕРЕПИСАН 2026-07-15: старый сборщик публичных матчей и
builds-подтаск удалены (воркер был выключен на сервере, паблик-логика
больше не нужна). Теперь единственная задача — статистика игроков
TI-команд с крупных турниров сезона через OpenDota, под помощник
официального фэнтези Dota 2 Compendium.

Запуск (отдельный процесс, как раньше):
    python -m backend.stats_updater

Логика цикла:
  1) /api/teams/{team_id}/matches для каждой TI-команды → фильтр по
     allowlist-лигам → новые match_id (которых нет в fantasy_player_stats);
  2) /api/matches/{match_id} → пер-игровые показатели ОБЕИХ сторон,
     принадлежащих TI-командам (матч TI-vs-TI пишется за один заход);
  3) upsert справочника fantasy_players (ник/команда — снапшот последнего
     матча, position из /proPlayers fantasy_role);
  4) сон FANTASY_POLL_MINUTES, повтор.

Идемпотентность: матч с заполненными metrics_json и полным gzip-снимком
OpenDota → пропуск. Старые строки без снимка автоматически перечитываются.
Rate limit: >=1.1с между запросами (OpenDota без ключа: 60/мин, ~3000/день).

ВАЖНО (исследование 2026-07-15): league_id проверены живыми запросами —
ранние 171xx-id оказались чужими лигами («Outback Inhouse» и т.п.).
Храним СЫРЫЕ показатели, не фэнтези-очки: механика TI2026 неизвестна,
формула станет конфигом после выхода компендиума.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from sqlalchemy import inspect, text

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.database import engine  # noqa: E402
from backend.fantasy_config import (  # noqa: E402
    FANTASY_ELIGIBILITY_OVERRIDES,
    FANTASY_LEAGUES,
    FANTASY_POSITION_OVERRIDES,
    OPENDOTA_FANTASY_ROLES,
    current_roster_players,
)
from backend.fantasy_metrics import (  # noqa: E402
    _num,
    compress_match_snapshot,
    extract_player_stats as _extract_player_stats,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("fantasy_updater")

OPENDOTA = "https://api.opendota.com/api"
API_KEY = os.environ.get("OPENDOTA_API_KEY", "").strip()

from backend.security_logging import configure_secure_logging  # noqa: E402

configure_secure_logging(API_KEY, os.environ.get("DATABASE_URL"))

# Пауза между запросами: без ключа лимит OpenDota 60/мин.
REQUEST_SLEEP_SECONDS = float(os.environ.get("FANTASY_SLEEP_SECONDS", "1.1"))
# Период полного прохода.
POLL_MINUTES = int(os.environ.get("FANTASY_POLL_MINUTES", "360"))
# Ограничение новых матчей за один проход (0 = без лимита) — для
# дозированного backfill'а и тестов.
MAX_MATCHES_PER_RUN = int(os.environ.get("FANTASY_MAX_MATCHES_PER_RUN", "0"))

# ── TI-команды: team_id подтверждены исследованием OpenDota 2026-07-15
# (у BoomBoys/Nigma/LGD/Spirit есть команды-дубли — ниже активные id). ──
TI_TEAMS: dict[int, str] = {
    9467224: "Aurora Gaming",
    8255888: "BetBoom Team",        # в OpenDota — «BoomBoys»
    10182357: "1w Team",
    9247354: "Team Falcons",
    2163: "Team Liquid",
    9823272: "Team Yandex",
    8261500: "Xtreme Gaming",
    7119388: "Team Spirit",
    9824702: "PARIVISION",          # актуальный OpenDota id (EWC 2026)
    9572001: "PARIVISION",          # прежний id, оставлен для истории
    10136357: "Nigma Galaxy",
    10149530: "HULIGANI",
    5017210: "Team Resilience",
    726228: "Vici Gaming",
    2586976: "OG",
    9964962: "GamerLegion",
    10150538: "LGD Gaming",
}

# OpenDota различает все три группы официального Fantasy:
# 1 — core, 2 — support, 4 — mid.
_FANTASY_ROLE_TO_POSITION = OPENDOTA_FANTASY_ROLES


# Типизированные колонки покрывают вероятные показатели компендиума и быстрые
# SQL-агрегаты. metrics_json ниже остаётся страховкой для новых счётчиков,
# которые Valve может объявить уже после релиза парсера.
_EXTRA_COLUMN_DDL: dict[str, str] = {
    "hero_id": "INTEGER",
    "duration": "INTEGER NOT NULL DEFAULT 0",
    "start_time": "BIGINT",
    "patch": "INTEGER",
    "win": "INTEGER NOT NULL DEFAULT 0",
    "denies": "INTEGER NOT NULL DEFAULT 0",
    "net_worth": "INTEGER NOT NULL DEFAULT 0",
    "hero_damage": "INTEGER NOT NULL DEFAULT 0",
    "hero_healing": "INTEGER NOT NULL DEFAULT 0",
    "tower_damage": "INTEGER NOT NULL DEFAULT 0",
    "sen_placed": "INTEGER NOT NULL DEFAULT 0",
    "rune_pickups": "INTEGER NOT NULL DEFAULT 0",
    "teamfight_participation": "FLOAT NOT NULL DEFAULT 0",
    "courier_kills": "INTEGER NOT NULL DEFAULT 0",
    "firstblood_claimed": "INTEGER NOT NULL DEFAULT 0",
    "smokes_used": "INTEGER NOT NULL DEFAULT 0",
    "watchers_taken": "INTEGER NOT NULL DEFAULT 0",
    "madstones_used": "INTEGER NOT NULL DEFAULT 0",
    "tormentor_kills": "INTEGER NOT NULL DEFAULT 0",
    "lotuses_used": "INTEGER NOT NULL DEFAULT 0",
    "buyback_count": "INTEGER NOT NULL DEFAULT 0",
    "metrics_json": "TEXT",
}

_EXTRA_PLAYER_COLUMN_DDL: dict[str, str] = {
    # TRUE сохраняет совместимость со строками, собранными до 0029. После
    # первого прохода current roster выставит точное значение.
    "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Схема (идемпотентно; прод — alembic 0023+0028+0029, dev-SQLite — этот же DDL)
# ─────────────────────────────────────────────────────────────────────────────

def ensure_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fantasy_players (
                account_id BIGINT PRIMARY KEY,
                name       VARCHAR(64),
                team_id    BIGINT,
                team_name  VARCHAR(64),
                position   VARCHAR(12),
                is_active  BOOLEAN NOT NULL DEFAULT TRUE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fantasy_player_stats (
                match_id      BIGINT  NOT NULL,
                account_id    BIGINT  NOT NULL,
                league_id     INTEGER NOT NULL,
                kills         INTEGER NOT NULL DEFAULT 0,
                deaths        INTEGER NOT NULL DEFAULT 0,
                assists       INTEGER NOT NULL DEFAULT 0,
                last_hits     INTEGER NOT NULL DEFAULT 0,
                gold_per_min  INTEGER NOT NULL DEFAULT 0,
                xp_per_min    INTEGER NOT NULL DEFAULT 0,
                stuns         FLOAT   NOT NULL DEFAULT 0,
                obs_placed    INTEGER NOT NULL DEFAULT 0,
                camps_stacked INTEGER NOT NULL DEFAULT 0,
                tower_kills   INTEGER NOT NULL DEFAULT 0,
                roshan_kills  INTEGER NOT NULL DEFAULT 0,
                hero_id       INTEGER,
                duration      INTEGER NOT NULL DEFAULT 0,
                start_time    BIGINT,
                patch         INTEGER,
                win           INTEGER NOT NULL DEFAULT 0,
                denies        INTEGER NOT NULL DEFAULT 0,
                net_worth     INTEGER NOT NULL DEFAULT 0,
                hero_damage   INTEGER NOT NULL DEFAULT 0,
                hero_healing  INTEGER NOT NULL DEFAULT 0,
                tower_damage  INTEGER NOT NULL DEFAULT 0,
                sen_placed    INTEGER NOT NULL DEFAULT 0,
                rune_pickups  INTEGER NOT NULL DEFAULT 0,
                teamfight_participation FLOAT NOT NULL DEFAULT 0,
                courier_kills INTEGER NOT NULL DEFAULT 0,
                firstblood_claimed INTEGER NOT NULL DEFAULT 0,
                smokes_used   INTEGER NOT NULL DEFAULT 0,
                watchers_taken INTEGER NOT NULL DEFAULT 0,
                madstones_used INTEGER NOT NULL DEFAULT 0,
                tormentor_kills INTEGER NOT NULL DEFAULT 0,
                lotuses_used  INTEGER NOT NULL DEFAULT 0,
                buyback_count INTEGER NOT NULL DEFAULT 0,
                metrics_json  TEXT,
                parsed_at     TIMESTAMP,
                PRIMARY KEY (match_id, account_id)
            )
        """))
        payload_type = "BYTEA" if conn.dialect.name == "postgresql" else "BLOB"
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS fantasy_match_snapshots (
                match_id       BIGINT PRIMARY KEY,
                league_id      INTEGER NOT NULL,
                payload_gzip   {payload_type} NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                parsed_at      TIMESTAMP
            )
        """))
        player_columns = {
            column["name"]
            for column in inspect(conn).get_columns("fantasy_players")
        }
        for column_name, ddl in _EXTRA_PLAYER_COLUMN_DDL.items():
            if column_name not in player_columns:
                conn.execute(text(
                    f"ALTER TABLE fantasy_players ADD COLUMN {column_name} {ddl}"
                ))

        existing_columns = {
            column["name"]
            for column in inspect(conn).get_columns("fantasy_player_stats")
        }
        for column_name, ddl in _EXTRA_COLUMN_DDL.items():
            if column_name not in existing_columns:
                # Имена/DDL — только из константы выше, пользовательского ввода нет.
                conn.execute(text(
                    f"ALTER TABLE fantasy_player_stats ADD COLUMN {column_name} {ddl}"
                ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_fantasy_player_stats_account "
            "ON fantasy_player_stats (account_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_fantasy_player_stats_league "
            "ON fantasy_player_stats (league_id)"
        ))


# ─────────────────────────────────────────────────────────────────────────────
#  OpenDota
# ─────────────────────────────────────────────────────────────────────────────

async def _od_get(client: httpx.AsyncClient, path: str) -> list | dict | None:
    """GET с паузой (rate limit) и одним ретраем на 429/5xx. None при неудаче."""
    params = {"api_key": API_KEY} if API_KEY else None
    for attempt in (1, 2):
        try:
            r = await client.get(OPENDOTA + path, params=params, timeout=40)
            await asyncio.sleep(REQUEST_SLEEP_SECONDS)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429 or r.status_code >= 500:
                logger.warning("[od] %s -> %d (attempt %d)", path, r.status_code, attempt)
                await asyncio.sleep(5.0 * attempt)
                continue
            logger.warning("[od] %s -> %d, giving up", path, r.status_code)
            return None
        except Exception as e:
            logger.warning("[od] %s failed: %s (attempt %d)", path, e, attempt)
            await asyncio.sleep(3.0 * attempt)
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Сбор
# ─────────────────────────────────────────────────────────────────────────────

def _known_match_ids() -> set:
    with engine.begin() as conn:
        rows = conn.execute(text(
            """
            SELECT s.match_id
            FROM fantasy_player_stats s
            JOIN fantasy_match_snapshots m ON m.match_id = s.match_id
            GROUP BY s.match_id
            HAVING COUNT(*) = SUM(
                CASE WHEN s.metrics_json IS NOT NULL THEN 1 ELSE 0 END
            )
            """
        )).fetchall()
    return {r[0] for r in rows}


async def _fetch_positions(client: httpx.AsyncClient) -> dict:
    """{account_id: 'core'|'mid'|'support'} из /proPlayers (best-effort)."""
    data = await _od_get(client, "/proPlayers")
    out: dict[int, str] = {}
    for p in data or []:
        pos = _FANTASY_ROLE_TO_POSITION.get(p.get("fantasy_role"))
        if pos and p.get("account_id"):
            out[int(p["account_id"])] = pos
    for account_id, position in FANTASY_POSITION_OVERRIDES.items():
        if position in {"core", "mid", "support"}:
            out[int(account_id)] = position
    logger.info("[fantasy] proPlayers positions loaded: %d", len(out))
    return out


def _refresh_saved_positions(positions: dict[int, str]) -> int:
    """Обновить роли уже известных игроков, даже если новых матчей нет."""
    if not positions:
        return 0
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE fantasy_players
                SET position = :position
                WHERE account_id = :account_id
                  AND (position IS NULL OR position <> :position)
            """),
            [
                {"account_id": account_id, "position": position}
                for account_id, position in positions.items()
            ],
        )
    return max(int(result.rowcount or 0), 0)


async def _refresh_current_rosters(
    client: httpx.AsyncClient,
) -> dict[int, set[int]]:
    """Синхронизировать eligibility по /teams/{id}/players.

    Команда обновляется только при успешном ответе OpenDota: временная ошибка
    API не должна скрыть весь её состав из рекомендаций.
    """
    active_by_team: dict[int, set[int]] = {}
    for team_id, team_name in TI_TEAMS.items():
        data = await _od_get(client, f"/teams/{team_id}/players")
        if data is None or not isinstance(data, list):
            logger.warning(
                "[fantasy] team %s (%d): roster fetch failed",
                team_name,
                team_id,
            )
            continue
        current = current_roster_players(data)
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE fantasy_players
                    SET is_active = FALSE
                    WHERE team_id = :team_id
                """),
                {"team_id": team_id},
            )
            for player in current:
                eligible = FANTASY_ELIGIBILITY_OVERRIDES.get(
                    player["account_id"],
                    True,
                )
                existing = conn.execute(
                    text("""
                        SELECT 1
                        FROM fantasy_players
                        WHERE account_id = :account_id
                    """),
                    {"account_id": player["account_id"]},
                ).fetchone()
                values = {
                    "account_id": player["account_id"],
                    "name": player["name"],
                    "team_id": team_id,
                    "team_name": team_name,
                    "is_active": bool(eligible),
                }
                if existing:
                    conn.execute(
                        text("""
                            UPDATE fantasy_players
                            SET name = COALESCE(:name, name),
                                team_id = :team_id,
                                team_name = :team_name,
                                is_active = :is_active
                            WHERE account_id = :account_id
                        """),
                        values,
                    )
                else:
                    conn.execute(
                        text("""
                            INSERT INTO fantasy_players
                                (account_id, name, team_id, team_name, position,
                                 is_active)
                            VALUES
                                (:account_id, :name, :team_id, :team_name, NULL,
                                 :is_active)
                        """),
                        values,
                    )
                if eligible:
                    active_by_team.setdefault(team_id, set()).add(
                        player["account_id"]
                    )
        active_by_team.setdefault(team_id, set())

    # Override применяется и к историческим игрокам, которых OpenDota больше
    # не возвращает в roster конкретной команды.
    if FANTASY_ELIGIBILITY_OVERRIDES:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE fantasy_players
                    SET is_active = :is_active
                    WHERE account_id = :account_id
                """),
                [
                    {
                        "account_id": int(account_id),
                        "is_active": bool(is_active),
                    }
                    for account_id, is_active
                    in FANTASY_ELIGIBILITY_OVERRIDES.items()
                ],
            )
    return active_by_team


def _store_match(
    match: dict,
    positions: dict,
    active_by_team: dict[int, set[int]] | None = None,
) -> int:
    """Пишет игроков TI-команд одного матча. Возвращает число строк."""
    league_id = match.get("leagueid")
    match_id = match.get("match_id")
    sides = {
        True: (match.get("radiant_team_id"), (match.get("radiant_team") or {}).get("name")),
        False: (match.get("dire_team_id"), (match.get("dire_team") or {}).get("name")),
    }
    now = datetime.now(timezone.utc)
    written = 0
    with engine.begin() as conn:
        # Нужен и для backfill старых строк: заменяем матч атомарно, чтобы
        # новые колонки и metrics_json не оставались с DEFAULT 0 навсегда.
        conn.execute(
            text("DELETE FROM fantasy_player_stats WHERE match_id = :match_id"),
            {"match_id": match_id},
        )
        snapshot = compress_match_snapshot(match)
        snapshot_exists = conn.execute(
            text(
                "SELECT 1 FROM fantasy_match_snapshots WHERE match_id = :match_id"
            ),
            {"match_id": match_id},
        ).fetchone()
        snapshot_values = {
            "match_id": match_id,
            "league_id": league_id,
            "payload_gzip": snapshot,
            "parsed_at": now,
        }
        if snapshot_exists:
            conn.execute(text("""
                UPDATE fantasy_match_snapshots
                SET league_id = :league_id, payload_gzip = :payload_gzip,
                    schema_version = 1, parsed_at = :parsed_at
                WHERE match_id = :match_id
            """), snapshot_values)
        else:
            conn.execute(text("""
                INSERT INTO fantasy_match_snapshots
                    (match_id, league_id, payload_gzip, schema_version, parsed_at)
                VALUES
                    (:match_id, :league_id, :payload_gzip, 1, :parsed_at)
            """), snapshot_values)
        for p in match.get("players") or []:
            acc = p.get("account_id")
            if not acc:
                continue
            team_id, team_name = sides.get(bool(p.get("isRadiant")), (None, None))
            if team_id not in TI_TEAMS:
                continue   # сторона не из TI-пула (матч TI vs не-TI)
            stats = _extract_player_stats(p)
            stats["start_time"] = int(_num(match.get("start_time"))) or None
            stats["patch"] = int(_num(match.get("patch"))) or None
            conn.execute(text("""
                INSERT INTO fantasy_player_stats
                    (match_id, account_id, league_id, kills, deaths, assists,
                     last_hits, gold_per_min, xp_per_min, stuns, obs_placed,
                     camps_stacked, tower_kills, roshan_kills, hero_id, duration,
                     start_time, patch, win, denies, net_worth, hero_damage,
                     hero_healing, tower_damage, sen_placed, rune_pickups,
                     teamfight_participation, courier_kills, firstblood_claimed,
                     smokes_used, watchers_taken, madstones_used, tormentor_kills,
                     lotuses_used, buyback_count, metrics_json, parsed_at)
                VALUES
                    (:match_id, :account_id, :league_id, :kills, :deaths, :assists,
                     :last_hits, :gold_per_min, :xp_per_min, :stuns, :obs_placed,
                     :camps_stacked, :tower_kills, :roshan_kills, :hero_id, :duration,
                     :start_time, :patch, :win, :denies, :net_worth, :hero_damage,
                     :hero_healing, :tower_damage, :sen_placed, :rune_pickups,
                     :teamfight_participation, :courier_kills, :firstblood_claimed,
                     :smokes_used, :watchers_taken, :madstones_used, :tormentor_kills,
                     :lotuses_used, :buyback_count, :metrics_json, :parsed_at)
            """), {
                "match_id": match_id, "account_id": acc, "league_id": league_id,
                "parsed_at": now, **stats,
            })
            # Справочник: ник/команда — снапшот свежайшего матча.
            name = (p.get("name") or p.get("personaname") or "").strip()[:64] or None
            canon_team = TI_TEAMS.get(team_id) or team_name
            team_roster = (
                active_by_team.get(team_id)
                if active_by_team is not None
                else None
            )
            eligibility_override = FANTASY_ELIGIBILITY_OVERRIDES.get(acc)
            if eligibility_override is not None:
                is_active = eligibility_override
            else:
                is_active = acc in team_roster if team_roster is not None else None
            existing = conn.execute(text(
                "SELECT 1 FROM fantasy_players WHERE account_id = :a"
            ), {"a": acc}).fetchone()
            if existing:
                conn.execute(text("""
                    UPDATE fantasy_players
                    SET name = COALESCE(:name, name), team_id = :tid,
                        team_name = :tname,
                        position = COALESCE(:pos, position),
                        is_active = COALESCE(:active, is_active)
                    WHERE account_id = :a
                """), {"a": acc, "name": name, "tid": team_id,
                       "tname": canon_team, "pos": positions.get(acc),
                       "active": is_active})
            else:
                conn.execute(text("""
                    INSERT INTO fantasy_players
                        (account_id, name, team_id, team_name, position, is_active)
                    VALUES (:a, :name, :tid, :tname, :pos, :active)
                """), {"a": acc, "name": name, "tid": team_id,
                       "tname": canon_team, "pos": positions.get(acc),
                       "active": True if is_active is None else is_active})
            written += 1
    return written


async def collect_once() -> None:
    """Один полный проход: команды → новые матчи → детали → запись."""
    known = _known_match_ids()
    logger.info("[fantasy] pass started; %d matches already stored", len(known))

    done = rows = failed = 0
    async with httpx.AsyncClient() as client:
        active_by_team = await _refresh_current_rosters(client)
        active_account_ids = {
            account_id
            for account_ids in active_by_team.values()
            for account_id in account_ids
        }
        logger.info(
            "[fantasy] current rosters refreshed: %d teams, %d active players",
            len(active_by_team),
            len(active_account_ids),
        )
        positions = await _fetch_positions(client)
        refreshed = _refresh_saved_positions(positions)
        if refreshed:
            logger.info("[fantasy] refreshed positions for %d saved players", refreshed)

        # 1) Дискавери: новые match_id по командам (dict сохраняет порядок).
        todo: dict[int, int] = {}   # match_id -> leagueid
        for team_id, label in TI_TEAMS.items():
            ms = await _od_get(client, f"/teams/{team_id}/matches")
            if ms is None:
                logger.warning("[fantasy] team %s (%d): matches fetch failed", label, team_id)
                continue
            fresh = 0
            for m in ms:
                lid = m.get("leagueid")
                mid = m.get("match_id")
                if lid in FANTASY_LEAGUES and mid and mid not in known and mid not in todo:
                    todo[mid] = lid
                    fresh += 1
            logger.info("[fantasy] %s: +%d new matches", label, fresh)

        match_ids = list(todo.keys())
        if MAX_MATCHES_PER_RUN > 0:
            match_ids = match_ids[:MAX_MATCHES_PER_RUN]
        logger.info("[fantasy] to fetch: %d matches%s", len(match_ids),
                    " (capped by FANTASY_MAX_MATCHES_PER_RUN)" if MAX_MATCHES_PER_RUN else "")

        # 2) Детали + запись.
        skipped_unparsed = 0
        for mid in match_ids:
            match = await _od_get(client, f"/matches/{mid}")
            if not match or not match.get("players"):
                failed += 1
                continue
            # Непропаршенный матч (version=null): скаляры уже есть, но
            # stuns/obs/camps отсутствуют → записали бы нули НАВСЕГДА
            # (идемпотентность по match_id). Пропускаем — подберём на
            # следующем проходе, когда OpenDota допарсит.
            if match.get("version") is None:
                skipped_unparsed += 1
                logger.info("[fantasy] match %s not parsed yet, deferred", mid)
                continue
            try:
                rows += _store_match(match, positions, active_by_team)
            except Exception as e:
                logger.warning("[fantasy] store %s failed: %s", mid, e)
                failed += 1
                continue
            done += 1
            if done % 10 == 0:
                logger.info("[fantasy] progress: %d/%d matches, %d player rows",
                            done, len(match_ids), rows)

    logger.info("[fantasy] pass done: %d matches stored, %d player rows, "
                "%d failed, %d deferred (unparsed)",
                done, rows, failed, skipped_unparsed)


async def run_loop() -> None:
    ensure_tables()
    logger.info("[fantasy] updater started: %d teams, %d leagues, poll=%dmin, key=%s",
                len(TI_TEAMS), len(FANTASY_LEAGUES), POLL_MINUTES,
                "yes" if API_KEY else "no")
    while True:
        t0 = time.monotonic()
        try:
            await collect_once()
        except Exception:
            logger.exception("[fantasy] pass crashed")
        logger.info("[fantasy] sleeping %d min (pass took %.0fs)",
                    POLL_MINUTES, time.monotonic() - t0)
        await asyncio.sleep(POLL_MINUTES * 60)


if __name__ == "__main__":
    asyncio.run(run_loop())
