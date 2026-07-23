# -*- coding: utf-8 -*-
"""Валидатор фэнтези-данных (fantasy_players / fantasy_player_stats).

Отвечает на вопрос «можно ли доверять напарсенному» без ручной сверки.
Четыре яруса проверок:

  A. Инварианты БД        — целостность без сети (лиги из вайтлиста, 5/10
                            строк на матч, справочник без сирот, диапазоны
                            значений, матчи-подозреваемые на «нули из-за
                            непропаршенности»).
  B. Спот-чек             — N случайных матчей перечитываются из OpenDota
                            и сверяются ПОЛЕ В ПОЛЕ с тем, что в БД
                            (ловит баги трансформации/записи).
  C. Правдоподобие        — агрегаты обязаны отражать реальность игры:
                            у кор GPM сильно выше, у саппортов вардов
                            сильно больше; выбросы печатаются.
  D. Полнота              — дискавери по /teams/{id}/matches заново и
                            сравнение с БД: какие матчи потеряны.

Запуск на сервере (DATABASE_URL из окружения):
    python -m backend.fantasy_validate                # всё, спот-чек 8 матчей
    python -m backend.fantasy_validate --spot 15      # больше спот-чека
    python -m backend.fantasy_validate --offline      # только ярус A и C (без сети)
    python -m backend.fantasy_validate --fix-unparsed # удалить строки матчей-
                                                      # «нулевиков» (парсер сам
                                                      # перечитает их следующим
                                                      # проходом)

Код возврата: 0 — ни одного FAIL, 1 — есть FAIL.
"""

import argparse
import logging
import random
import sys
import time

logging.getLogger("httpx").setLevel(logging.WARNING)

import httpx
from sqlalchemy import text

from backend.database import engine
from backend.stats_updater import (
    API_KEY,
    FANTASY_LEAGUES,
    OPENDOTA,
    REQUEST_SLEEP_SECONDS,
    TI_TEAMS,
    _extract_player_stats,
)

FAILS: list[str] = []
WARNS: list[str] = []

# Поля stats-строки, сверяемые в спот-чеке (имя колонки = ключ экстрактора).
_STAT_FIELDS = (
    "kills", "deaths", "assists", "last_hits", "gold_per_min", "xp_per_min",
    "stuns", "obs_placed", "camps_stacked", "tower_kills", "roshan_kills",
    "denies", "net_worth", "hero_damage", "hero_healing", "tower_damage",
    "sen_placed", "rune_pickups", "teamfight_participation", "courier_kills",
    "firstblood_claimed", "smokes_used", "watchers_taken", "madstones_used",
    "tormentor_kills", "lotuses_used", "buyback_count", "duration", "win",
)

# Санитарные диапазоны для про-матча (за пределами — не «невозможно»,
# а «надо посмотреть глазами», поэтому WARN, не FAIL).
_RANGES = {
    "kills": (0, 40), "deaths": (0, 35), "assists": (0, 60),
    "last_hits": (0, 1600), "gold_per_min": (80, 1500),
    "xp_per_min": (80, 1800), "stuns": (0, 300), "obs_placed": (0, 80),
    "camps_stacked": (0, 40), "tower_kills": (0, 12), "roshan_kills": (0, 8),
    "denies": (0, 200), "net_worth": (0, 100000),
    "hero_damage": (0, 500000), "hero_healing": (0, 200000),
    "tower_damage": (0, 100000), "sen_placed": (0, 80),
    "rune_pickups": (0, 100), "teamfight_participation": (0, 1),
    "courier_kills": (0, 20), "firstblood_claimed": (0, 1),
    "smokes_used": (0, 30), "watchers_taken": (0, 30),
    "madstones_used": (0, 50), "tormentor_kills": (0, 10),
    "lotuses_used": (0, 50), "buyback_count": (0, 10),
}


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def _warn(msg: str) -> None:
    WARNS.append(msg)
    print(f"  WARN  {msg}")


def _fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"  FAIL  {msg}")


def _od(client: httpx.Client, path: str):
    params = {"api_key": API_KEY} if API_KEY else None
    for attempt in (1, 2):
        try:
            r = client.get(OPENDOTA + path, params=params, timeout=40)
            time.sleep(REQUEST_SLEEP_SECONDS)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5.0 * attempt)
                continue
            return None
        except Exception:
            time.sleep(3.0 * attempt)
    return None


# ────────────────────────────────────────────────────────────────────────────
#  A. Инварианты БД
# ────────────────────────────────────────────────────────────────────────────

def check_invariants() -> list[int]:
    """Возвращает match_id матчей-«нулевиков» (для --fix-unparsed)."""
    print("\n─── A. Инварианты БД ───")
    with engine.begin() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM fantasy_player_stats")).scalar()
        matches = conn.execute(text(
            "SELECT COUNT(DISTINCT match_id) FROM fantasy_player_stats")).scalar()
        players = conn.execute(text("SELECT COUNT(*) FROM fantasy_players")).scalar()
        print(f"  ИТОГО: {total} строк, {matches} матчей, {players} игроков в справочнике")
        if not total:
            _fail("таблица fantasy_player_stats пуста")
            return []

        missing_snapshots = conn.execute(text("""
            SELECT COUNT(DISTINCT s.match_id)
            FROM fantasy_player_stats s
            LEFT JOIN fantasy_match_snapshots m ON m.match_id = s.match_id
            WHERE m.match_id IS NULL OR m.payload_gzip IS NULL
        """)).scalar()
        if missing_snapshots:
            _fail(f"{missing_snapshots} матчей без полного gzip-снимка OpenDota")
        else:
            _ok("у каждого матча есть полный gzip-снимок OpenDota")

        # Лиги строго из вайтлиста.
        bad_leagues = conn.execute(text(
            "SELECT DISTINCT league_id FROM fantasy_player_stats")).fetchall()
        alien = [r[0] for r in bad_leagues if r[0] not in FANTASY_LEAGUES]
        if alien:
            _fail(f"чужие league_id в данных: {alien}")
        else:
            _ok(f"все league_id из вайтлиста ({len(bad_leagues)} лиг встречено)")

        # На матч должно быть ровно 5 (TI vs не-TI) или 10 (TI vs TI) строк.
        odd = conn.execute(text("""
            SELECT match_id, COUNT(*) AS c FROM fantasy_player_stats
            GROUP BY match_id HAVING COUNT(*) NOT IN (5, 10)
        """)).fetchall()
        if odd:
            _fail(f"матчи с числом строк не 5/10: {[(r[0], r[1]) for r in odd[:10]]}")
        else:
            _ok("в каждом матче ровно 5 или 10 строк")

        # Каждый account_id из stats есть в справочнике.
        orphans = conn.execute(text("""
            SELECT COUNT(DISTINCT s.account_id) FROM fantasy_player_stats s
            LEFT JOIN fantasy_players p ON p.account_id = s.account_id
            WHERE p.account_id IS NULL
        """)).scalar()
        if orphans:
            _fail(f"{orphans} account_id из stats отсутствуют в fantasy_players")
        else:
            _ok("справочник покрывает всех игроков из stats")

        # Команды справочника — только TI-пул.
        alien_teams = conn.execute(text(
            "SELECT DISTINCT team_id FROM fantasy_players")).fetchall()
        bad_t = [r[0] for r in alien_teams if r[0] not in TI_TEAMS]
        if bad_t:
            _fail(f"team_id вне TI-пула в справочнике: {bad_t}")
        else:
            _ok(f"все команды из TI-пула ({len(alien_teams)} team_id)")

        # Диапазоны значений.
        range_hits = 0
        for field, (lo, hi) in _RANGES.items():
            rows = conn.execute(text(
                f"SELECT match_id, account_id, {field} FROM fantasy_player_stats "
                f"WHERE {field} < :lo OR {field} > :hi"
            ), {"lo": lo, "hi": hi}).fetchall()
            for r in rows[:5]:
                _warn(f"{field}={r[2]} вне диапазона [{lo},{hi}] "
                      f"(match {r[0]}, account {r[1]})")
            range_hits += len(rows)
        if not range_hits:
            _ok("все значения в санитарных диапазонах")

        # «Нулевики»: суммарно stuns+obs+camps по матчу = 0 — почти наверняка
        # матч записан НЕпропаршенным (нули вместо реальных значений).
        zero_matches = conn.execute(text("""
            SELECT match_id FROM fantasy_player_stats
            GROUP BY match_id
            HAVING SUM(stuns) + SUM(obs_placed) + SUM(camps_stacked) = 0
        """)).fetchall()
        zero_ids = [r[0] for r in zero_matches]
        if zero_ids:
            _fail(f"{len(zero_ids)} матчей-«нулевиков» (записаны до парсинга "
                  f"OpenDota, parsed-поля = 0): {zero_ids[:15]}"
                  f"{' …' if len(zero_ids) > 15 else ''} — чинится --fix-unparsed")
        else:
            _ok("матчей-«нулевиков» нет (все записаны пропаршенными)")

        # Позиция обязательна только для активных Fantasy-игроков. Исторические
        # стендины, тренеры и прочие исключённые записи могут оставаться NULL:
        # они нужны справочнику, но не попадают в рекомендации.
        nopos = conn.execute(text(
            """
            SELECT COUNT(*)
            FROM fantasy_players
            WHERE position IS NULL AND is_active = TRUE
            """
        )).scalar()
        if nopos:
            _warn(f"{nopos} активных игроков без position — "
                  f"проверить вручную только их")
        else:
            _ok("у всех активных игроков есть position")
    return zero_ids


# ────────────────────────────────────────────────────────────────────────────
#  B. Спот-чек против OpenDota
# ────────────────────────────────────────────────────────────────────────────

def check_spot(client: httpx.Client, n: int) -> None:
    print(f"\n─── B. Спот-чек: {n} случайных матчей против OpenDota ───")
    with engine.begin() as conn:
        all_ids = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT match_id FROM fantasy_player_stats")).fetchall()]
    if not all_ids:
        return
    sample = random.sample(all_ids, min(n, len(all_ids)))
    mismatches = 0
    for mid in sample:
        od = _od(client, f"/matches/{mid}")
        if not od or not od.get("players"):
            _warn(f"match {mid}: не удалось перечитать из OpenDota, пропущен")
            continue
        od_by_acc = {p.get("account_id"): p for p in od["players"] if p.get("account_id")}
        with engine.begin() as conn:
            db_rows = conn.execute(text(
                "SELECT * FROM fantasy_player_stats WHERE match_id = :m"
            ), {"m": mid}).mappings().fetchall()
        match_ok = True
        for row in db_rows:
            p = od_by_acc.get(row["account_id"])
            if p is None:
                _fail(f"match {mid}: account {row['account_id']} есть в БД, "
                      f"но нет в матче OpenDota")
                match_ok = False
                continue
            fresh = _extract_player_stats(p)
            for f in _STAT_FIELDS:
                db_v, od_v = row[f], fresh[f]
                if f in {"stuns", "teamfight_participation"}:
                    same = abs(float(db_v) - float(od_v)) < 0.01
                else:
                    same = int(db_v) == int(od_v)
                if not same:
                    _fail(f"match {mid}, account {row['account_id']}: "
                          f"{f} БД={db_v} vs OpenDota={od_v}")
                    match_ok = False
                    mismatches += 1
        if match_ok:
            _ok(f"match {mid}: {len(db_rows)} строк — полное совпадение")
    if not mismatches:
        print(f"  → расхождений полей: 0")


# ────────────────────────────────────────────────────────────────────────────
#  C. Правдоподобие агрегатов
# ────────────────────────────────────────────────────────────────────────────

def check_plausibility() -> None:
    print("\n─── C. Правдоподобие агрегатов ───")
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT p.position, AVG(s.gold_per_min) AS gpm, AVG(s.obs_placed) AS obs,
                   AVG(s.last_hits) AS lh, COUNT(*) AS n
            FROM fantasy_player_stats s
            JOIN fantasy_players p ON p.account_id = s.account_id
            WHERE p.position IS NOT NULL
            GROUP BY p.position
        """)).mappings().fetchall()
        by_pos = {r["position"]: r for r in rows}
        core, supp = by_pos.get("core"), by_pos.get("support")
        if core and supp:
            print(f"  core:    GPM {core['gpm']:.0f}, обсы {core['obs']:.1f}, "
                  f"ластхиты {core['lh']:.0f}  (n={core['n']})")
            print(f"  support: GPM {supp['gpm']:.0f}, обсы {supp['obs']:.1f}, "
                  f"ластхиты {supp['lh']:.0f}  (n={supp['n']})")
            if core["gpm"] - supp["gpm"] > 100:
                _ok("GPM кор существенно выше саппортов — данные отражают роли")
            else:
                _fail(f"GPM core≈support ({core['gpm']:.0f} vs {supp['gpm']:.0f}) — "
                      f"роли перепутаны или данные битые")
            if supp["obs"] > core["obs"] * 2:
                _ok("вардинг у саппортов кратно выше — правдоподобно")
            else:
                _fail(f"обсы support={supp['obs']:.1f} vs core={core['obs']:.1f} — "
                      f"подозрительно")
        else:
            _warn("нет разметки core/support для сравнения ролей")

        # Топ по среднему GPM — глазами сверить с известными игроками.
        top = conn.execute(text("""
            SELECT p.name, p.team_name, AVG(s.gold_per_min) AS gpm, COUNT(*) AS n
            FROM fantasy_player_stats s
            JOIN fantasy_players p ON p.account_id = s.account_id
            GROUP BY s.account_id, p.name, p.team_name
            HAVING COUNT(*) >= 5
            ORDER BY gpm DESC LIMIT 5
        """)).mappings().fetchall()
        print("  Топ-5 по ср. GPM (сверь с ожиданиями — должны быть известные керри):")
        for t in top:
            print(f"    {t['gpm']:.0f} GPM  {t['name'] or '?'} ({t['team_name']}, "
                  f"{t['n']} матчей)")

        # Разброс матчей на игрока: заметно «тощие» игроки в основе — повод
        # проверить полноту (стендины/новички — норма).
        cnt = conn.execute(text("""
            SELECT p.name, p.team_name, COUNT(*) AS n
            FROM fantasy_player_stats s
            JOIN fantasy_players p ON p.account_id = s.account_id
            GROUP BY s.account_id, p.name, p.team_name
            ORDER BY n ASC LIMIT 5
        """)).mappings().fetchall()
        print("  Минимум матчей (стендины — норма, основа — повод проверить):")
        for t in cnt:
            print(f"    {t['n']:>3}  {t['name'] or '?'} ({t['team_name']})")


# ────────────────────────────────────────────────────────────────────────────
#  D. Полнота (повторное дискавери против БД)
# ────────────────────────────────────────────────────────────────────────────

def check_completeness(client: httpx.Client) -> None:
    print("\n─── D. Полнота: дискавери заново против БД ───")
    expected: set[int] = set()
    for team_id, label in TI_TEAMS.items():
        ms = _od(client, f"/teams/{team_id}/matches")
        if ms is None:
            _warn(f"{label}: /teams/{team_id}/matches недоступен, команда пропущена")
            continue
        for m in ms:
            if m.get("leagueid") in FANTASY_LEAGUES and m.get("match_id"):
                expected.add(m["match_id"])
    with engine.begin() as conn:
        stored = {r[0] for r in conn.execute(text(
            "SELECT DISTINCT match_id FROM fantasy_player_stats")).fetchall()}
    missing = sorted(expected - stored)
    extra = sorted(stored - expected)
    print(f"  Ожидается по дискавери: {len(expected)}, в БД: {len(stored)}")
    if missing:
        _warn(f"{len(missing)} матчей ещё не в БД (свежие/отложенные — парсер "
              f"дособерёт; давние — разбираться): {missing[:15]}"
              f"{' …' if len(missing) > 15 else ''}")
    else:
        _ok("все обнаруженные матчи сохранены")
    if extra:
        _warn(f"{len(extra)} матчей в БД, которых нет в дискавери "
              f"(команда меняла состав/id?): {extra[:10]}")
    else:
        _ok("лишних матчей в БД нет")


def fix_unparsed(zero_ids: list[int]) -> None:
    if not zero_ids:
        print("\nНечего чинить: «нулевиков» нет.")
        return
    with engine.begin() as conn:
        for mid in zero_ids:
            conn.execute(text(
                "DELETE FROM fantasy_player_stats WHERE match_id = :m"), {"m": mid})
    print(f"\nУдалены строки {len(zero_ids)} матчей-«нулевиков» — парсер "
          f"перечитает их следующим проходом (уже пропаршенными).")


def main() -> int:
    ap = argparse.ArgumentParser(description="Валидатор фэнтези-данных")
    ap.add_argument("--spot", type=int, default=8,
                    help="сколько матчей перечитать из OpenDota (ярус B)")
    ap.add_argument("--offline", action="store_true",
                    help="только ярусы A и C, без обращений к OpenDota")
    ap.add_argument("--fix-unparsed", action="store_true",
                    help="удалить строки матчей-«нулевиков» для перечитки")
    args = ap.parse_args()

    zero_ids = check_invariants()
    check_plausibility()
    if not args.offline:
        with httpx.Client() as client:
            if args.spot > 0:
                check_spot(client, args.spot)
            check_completeness(client)

    if args.fix_unparsed:
        fix_unparsed(zero_ids)

    print(f"\n══ ИТОГ: {len(FAILS)} FAIL, {len(WARNS)} WARN ══")
    if FAILS:
        print("Данным в текущем виде доверять нельзя — см. FAIL выше.")
    elif WARNS:
        print("Критичных проблем нет; WARN — на просмотр глазами.")
    else:
        print("Все проверки чистые — данные соответствуют OpenDota и здравому смыслу.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
