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

Идемпотентность: match_id уже в fantasy_player_stats → пропуск.
Rate limit: >=1.1с между запросами (OpenDota без ключа: 60/мин, ~3000/день).

ВАЖНО (исследование 2026-07-15): league_id проверены живыми запросами —
ранние 171xx-id оказались чужими лигами («Outback Inhouse» и т.п.).
Храним СЫРЫЕ показатели, не фэнтези-очки: механика TI2026 неизвестна,
формула станет конфигом после выхода компендиума.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.database import engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("fantasy_updater")

OPENDOTA = "https://api.opendota.com/api"
API_KEY = os.environ.get("OPENDOTA_API_KEY", "").strip()

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
    9572001: "PARIVISION",          # в OpenDota — «TEAM VISION»
    10136357: "Nigma Galaxy",
    10149530: "HULIGANI",
    5017210: "Team Resilience",
    726228: "Vici Gaming",
    2586976: "OG",
    9964962: "GamerLegion",
    10150538: "LGD Gaming",
}

# ── Турниры сезона: id ПРОВЕРЕНЫ (изначальные 171xx были чужими лигами). ──
FANTASY_LEAGUES: dict[int, str] = {
    19785: "EWC 2026",
    19101: "BLAST SLAM VII",
    19099: "BLAST SLAM VI",
    19269: "DreamLeague S28",
    19696: "DreamLeague S29",
    19435: "PGL Wallachia S7",
    19543: "PGL Wallachia S8",
    19422: "ESL One Birmingham 2026",
}

# OpenDota fantasy_role → наша position ('mid' OpenDota не различает —
# уточнится ручной разметкой на этапе 2, когда выйдет компендиум).
_FANTASY_ROLE_TO_POSITION = {1: "core", 2: "support"}


# ─────────────────────────────────────────────────────────────────────────────
#  Схема (идемпотентно; прод — alembic 0023, dev-SQLite — этот же DDL)
# ─────────────────────────────────────────────────────────────────────────────

def ensure_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fantasy_players (
                account_id BIGINT PRIMARY KEY,
                name       VARCHAR(64),
                team_id    BIGINT,
                team_name  VARCHAR(64),
                position   VARCHAR(12)
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
                parsed_at     TIMESTAMP,
                PRIMARY KEY (match_id, account_id)
            )
        """))
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


def _num(v, default=0):
    """tower_kills/roshan_kills и пр. бывают null → 0."""
    return default if v is None else v


def _extract_player_stats(p: dict) -> dict:
    return {
        "kills": int(_num(p.get("kills"))),
        "deaths": int(_num(p.get("deaths"))),
        "assists": int(_num(p.get("assists"))),
        "last_hits": int(_num(p.get("last_hits"))),
        "gold_per_min": int(_num(p.get("gold_per_min"))),
        "xp_per_min": int(_num(p.get("xp_per_min"))),
        "stuns": float(_num(p.get("stuns"), 0.0)),
        "obs_placed": int(_num(p.get("obs_placed"))),
        "camps_stacked": int(_num(p.get("camps_stacked"))),
        # оба имени существуют в API и равны — берём любое присутствующее
        "tower_kills": int(_num(p.get("tower_kills", p.get("towers_killed")))),
        "roshan_kills": int(_num(p.get("roshan_kills", p.get("roshans_killed")))),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Сбор
# ─────────────────────────────────────────────────────────────────────────────

def _known_match_ids() -> set:
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT match_id FROM fantasy_player_stats"
        )).fetchall()
    return {r[0] for r in rows}


async def _fetch_positions(client: httpx.AsyncClient) -> dict:
    """{account_id: 'core'|'support'} из /proPlayers (best-effort)."""
    data = await _od_get(client, "/proPlayers")
    out: dict[int, str] = {}
    for p in data or []:
        pos = _FANTASY_ROLE_TO_POSITION.get(p.get("fantasy_role"))
        if pos and p.get("account_id"):
            out[int(p["account_id"])] = pos
    logger.info("[fantasy] proPlayers positions loaded: %d", len(out))
    return out


def _store_match(match: dict, positions: dict) -> int:
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
        for p in match.get("players") or []:
            acc = p.get("account_id")
            if not acc:
                continue
            team_id, team_name = sides.get(bool(p.get("isRadiant")), (None, None))
            if team_id not in TI_TEAMS:
                continue   # сторона не из TI-пула (матч TI vs не-TI)
            stats = _extract_player_stats(p)
            conn.execute(text("""
                INSERT INTO fantasy_player_stats
                    (match_id, account_id, league_id, kills, deaths, assists,
                     last_hits, gold_per_min, xp_per_min, stuns, obs_placed,
                     camps_stacked, tower_kills, roshan_kills, parsed_at)
                VALUES
                    (:match_id, :account_id, :league_id, :kills, :deaths, :assists,
                     :last_hits, :gold_per_min, :xp_per_min, :stuns, :obs_placed,
                     :camps_stacked, :tower_kills, :roshan_kills, :parsed_at)
            """), {
                "match_id": match_id, "account_id": acc, "league_id": league_id,
                "parsed_at": now, **stats,
            })
            # Справочник: ник/команда — снапшот свежайшего матча.
            name = (p.get("name") or p.get("personaname") or "").strip()[:64] or None
            canon_team = TI_TEAMS.get(team_id) or team_name
            existing = conn.execute(text(
                "SELECT 1 FROM fantasy_players WHERE account_id = :a"
            ), {"a": acc}).fetchone()
            if existing:
                conn.execute(text("""
                    UPDATE fantasy_players
                    SET name = COALESCE(:name, name), team_id = :tid,
                        team_name = :tname,
                        position = COALESCE(:pos, position)
                    WHERE account_id = :a
                """), {"a": acc, "name": name, "tid": team_id,
                       "tname": canon_team, "pos": positions.get(acc)})
            else:
                conn.execute(text("""
                    INSERT INTO fantasy_players (account_id, name, team_id, team_name, position)
                    VALUES (:a, :name, :tid, :tname, :pos)
                """), {"a": acc, "name": name, "tid": team_id,
                       "tname": canon_team, "pos": positions.get(acc)})
            written += 1
    return written


async def collect_once() -> None:
    """Один полный проход: команды → новые матчи → детали → запись."""
    known = _known_match_ids()
    logger.info("[fantasy] pass started; %d matches already stored", len(known))

    done = rows = failed = 0
    async with httpx.AsyncClient() as client:
        positions = await _fetch_positions(client)

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
        for mid in match_ids:
            match = await _od_get(client, f"/matches/{mid}")
            if not match or not match.get("players"):
                failed += 1
                continue
            try:
                rows += _store_match(match, positions)
            except Exception as e:
                logger.warning("[fantasy] store %s failed: %s", mid, e)
                failed += 1
                continue
            done += 1
            if done % 10 == 0:
                logger.info("[fantasy] progress: %d/%d matches, %d player rows",
                            done, len(match_ids), rows)

    logger.info("[fantasy] pass done: %d matches stored, %d player rows, %d failed",
                done, rows, failed)


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
