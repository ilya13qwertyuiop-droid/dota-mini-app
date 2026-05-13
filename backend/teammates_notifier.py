"""
teammates_notifier.py — async worker that sends review reminders ~90 min
after a teammate request was accepted.

Архитектурно зеркалит backend/stats_updater.py и news_updater.py: модуль
выставляет async-функцию `run_loop()`, его можно запустить отдельным
процессом:

    python -m backend.teammates_notifier

Опционально функцию `process_pending_reviews()` можно дёрнуть из другого
места (например, периодически из bot.py / stats_updater.py), если вы
не хотите содержать четвёртый процесс.

Состояние живёт в БД: `teammate_requests.review_sent` выставляется в TRUE
после успешной доставки напоминания. Колонка уже создана миграцией 0007
ровно под эту задачу — никаких новых миграций не требуется.

Идемпотентность: атомарный claim через
    UPDATE teammate_requests
    SET review_sent = TRUE
    WHERE id = :id AND review_sent = FALSE
гарантирует, что даже при параллельных воркерах напоминание уйдёт ровно
один раз. На single-worker-деплое это бесплатная страховка.

Конфигурация через переменные окружения:
    TM_REVIEW_DELAY_MINUTES    — задержка перед напоминанием (default 90)
    TM_NOTIFIER_INTERVAL_SEC   — период поллинга (default 60)
    TM_NOTIFIER_BATCH_SIZE     — макс. напоминаний за один проход (default 100)
    BOT_TOKEN                  — токен бота (обязательно)
    MINI_APP_URL               — база URL миниапа для deep-link'а кнопки
                                 (если не задан — сообщение уйдёт без кнопки)
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text

from backend.database import SessionLocal

logger = logging.getLogger(__name__)

BOT_TOKEN: str | None = os.environ.get("BOT_TOKEN")
MINI_APP_URL: str | None = os.environ.get("MINI_APP_URL")

REVIEW_DELAY_MINUTES   = int(os.environ.get("TM_REVIEW_DELAY_MINUTES", "90"))
POLL_INTERVAL_SECONDS  = int(os.environ.get("TM_NOTIFIER_INTERVAL_SEC", "60"))
BATCH_SIZE             = int(os.environ.get("TM_NOTIFIER_BATCH_SIZE", "100"))

# Текст напоминания. Краткий, без эмодзи-перебора (Linear-style), с прозрачной
# мотивацией: «зачем тебе тратить 10 секунд на отзыв».
REMINDER_TEXT = (
    "⏱️ Прошло полтора часа после игры. Оцени тиммейта — "
    "это поможет другим игрокам выбирать лучших напарников."
)


def _review_url(request_id: int, target_user_id: int) -> str | None:
    """Deep-link на экран отзыва. None — если MINI_APP_URL не задан.

    Совместим с фронтовым `_tmCheckDeepLink` (script.js): query-параметры
    teammate_review/teammate_target открывают page-teammate-review с
    предзагрузкой профиля оцениваемого игрока.
    """
    if not MINI_APP_URL:
        return None
    return f"{MINI_APP_URL}?teammate_review={request_id}&teammate_target={target_user_id}"


async def _send_review_reminder(
    client: httpx.AsyncClient,
    chat_id: int,
    button_url: str | None,
) -> bool:
    """Один sendMessage. Возвращает True, если Telegram принял запрос.

    Все ошибки только логируются — fire-and-forget по тому же контракту,
    что и `_tm_send_bot_message` в api.py.
    """
    if not BOT_TOKEN:
        return False
    payload: dict = {
        "chat_id": chat_id,
        "text": REMINDER_TEXT,
        "disable_web_page_preview": True,
    }
    if button_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "Оценить игрока", "web_app": {"url": button_url}},
            ]],
        }
    try:
        r = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=5.0,
        )
        if r.status_code != 200:
            logger.warning(
                "[tm_notifier] sendMessage chat_id=%s failed: %d %s",
                chat_id, r.status_code, (r.text or "")[:200],
            )
            return False
        return True
    except Exception as e:
        logger.warning("[tm_notifier] sendMessage chat_id=%s error: %s", chat_id, e)
        return False


async def process_pending_reviews() -> int:
    """Один проход воркера: выбрать просроченные accepted-запросы, разослать
    напоминания, отметить как доставленные.

    Возвращает число запросов, по которым ушло хотя бы одно сообщение из двух
    (то есть UI-видимое количество, не сумма сообщений).

    Примечание про SQL: SELECT/UPDATE здесь — RAW text() намеренно. С ORM-фильтром
    `TeammateRequest.review_sent.is_(False)` запрос на PostgreSQL приходил
    пустым даже когда строки реально есть. Видимо, на конкретной комбинации
    SQLAlchemy + psycopg2 .is_(False) для Boolean-колонки превращается во что-то,
    что не матчит хранимое FALSE. Raw `review_sent = FALSE` ведёт себя
    предсказуемо (и побайтово совпадает с тем, что находит psql).

    Примечание про TZ: cutoff обязан быть TIMEZONE-AWARE (UTC), а НЕ результат
    `datetime.utcnow()`. Причина:
      - api.py пишет `accepted_at = datetime.now(timezone.utc)` — tz-aware.
      - На PostgreSQL c session TZ != UTC (например Europe/Berlin) psycopg2 при
        INSERT-е конвертит tz-aware значение в session TZ и кладёт в
        `TIMESTAMP WITHOUT TIME ZONE` колонку как локальное wall-clock-время
        (т.е. Berlin), без какой-либо tz-метки.
      - Если передать cutoff как naive UTC (`datetime.utcnow()`), PG сравнит
        наивное число с наивным числом — две разные временные шкалы как одни
        и те же значения. Результат: дыра размером с TZ-offset, в которой
        свежеподошедшие строки не находятся.
      - Tz-aware cutoff (timestamptz на стороне PG) заставляет PG implicit-
        cast'нуть `accepted_at` к timestamptz через session TZ, и сравнение
        идёт по абсолютным моментам времени — корректно при любом server TZ.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=REVIEW_DELAY_MINUTES)

    # 1) Выбираем кандидатов одним запросом. Поля выбираем явно — нам нужны
    #    только id и два user_id для отправки.
    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT id, from_user_id, to_user_id
                FROM teammate_requests
                WHERE status = 'accepted'
                  AND review_sent = FALSE
                  AND accepted_at IS NOT NULL
                  AND accepted_at <= :cutoff
                ORDER BY accepted_at ASC
                LIMIT :batch_size
                """
            ),
            {"cutoff": cutoff, "batch_size": BATCH_SIZE},
        ).fetchall()

    if not rows:
        return 0

    logger.info("[tm_notifier] %d request(s) due for reminder", len(rows))

    sent_count = 0
    async with httpx.AsyncClient() as client:
        for row in rows:
            req_id, from_user_id, to_user_id = row[0], row[1], row[2]

            # 2) Атомарный claim — UPDATE … WHERE review_sent=FALSE.
            #    rowcount=0 значит, что флаг уже выставлен (другой воркер,
            #    ручная правка). Тогда мы НЕ пытаемся слать повторно.
            with SessionLocal() as session:
                result = session.execute(
                    text(
                        """
                        UPDATE teammate_requests
                        SET review_sent = TRUE
                        WHERE id = :id AND review_sent = FALSE
                        """
                    ),
                    {"id": req_id},
                )
                rowcount = result.rowcount
                session.commit()

            if not rowcount:
                continue

            # 3) У каждого участника свой target — оцениваешь ДРУГОГО.
            url_for_from = _review_url(req_id, to_user_id)
            url_for_to   = _review_url(req_id, from_user_id)

            ok_from = await _send_review_reminder(client, from_user_id, url_for_from)
            ok_to   = await _send_review_reminder(client, to_user_id,   url_for_to)

            if ok_from or ok_to:
                sent_count += 1
                logger.info(
                    "[tm_notifier] request=%d notified: from_user=%s to_user=%s",
                    req_id, ok_from, ok_to,
                )
            else:
                # 4) Полный отказ обоих — откатываем флаг, попробуем ещё раз
                # на следующем цикле. Сценарии: Telegram API лёг целиком, оба
                # юзера заблокировали бота, или сетевая ошибка httpx.
                # Частичный успех НЕ откатываем — иначе при ретрае спам успешному.
                with SessionLocal() as session:
                    session.execute(
                        text(
                            """
                            UPDATE teammate_requests
                            SET review_sent = FALSE
                            WHERE id = :id
                            """
                        ),
                        {"id": req_id},
                    )
                    session.commit()
                logger.warning(
                    "[tm_notifier] both sends failed for request=%d, "
                    "rolled back for retry next cycle", req_id,
                )

    return sent_count


# ─────────────────────────────────────────────────────────────────────────────
#  Lobby expiry: party-finder лобби со status='open' и истёкшим expires_at
#  переводятся в 'expired', участникам отправляется уведомление.
# ─────────────────────────────────────────────────────────────────────────────


async def process_expired_lobbies() -> int:
    """Один проход воркера для лобби. Возвращает число expired лобби."""
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT id, host_id
                FROM teammate_lobbies
                WHERE status = 'open'
                  AND expires_at <= :now
                ORDER BY expires_at ASC
                LIMIT :batch
                """
            ),
            {"now": now, "batch": BATCH_SIZE},
        ).fetchall()

    if not rows:
        return 0

    logger.info("[tm_notifier] %d lobby/lobbies expired", len(rows))

    expired_count = 0
    async with httpx.AsyncClient() as client:
        for row in rows:
            lobby_id, host_id = row[0], row[1]

            # Атомарно меняем status. rowcount=0 значит «уже не open» —
            # параллельный воркер / disband / fill. Тогда пропускаем.
            with SessionLocal() as session:
                result = session.execute(
                    text(
                        """
                        UPDATE teammate_lobbies
                        SET status = 'expired'
                        WHERE id = :id AND status = 'open'
                        """
                    ),
                    {"id": lobby_id},
                )
                rowcount = result.rowcount
                session.commit()

            if not rowcount:
                continue
            expired_count += 1

            # Собираем members лобби (без host'а — ему отдельный текст).
            with SessionLocal() as session:
                member_rows = session.execute(
                    text(
                        """
                        SELECT user_id
                        FROM teammate_lobby_slots
                        WHERE lobby_id = :id
                          AND user_id IS NOT NULL
                          AND user_id <> :host
                        """
                    ),
                    {"id": lobby_id, "host": host_id},
                ).fetchall()
                member_ids = [r[0] for r in member_rows]

            # Host: «не собралось». Members: «лобби распущено по таймеру».
            await _send_simple_message(
                client,
                host_id,
                "⏱️ Лобби не собралось за 30 минут. Попробуй позже.",
            )
            for mid in member_ids:
                await _send_simple_message(
                    client, mid, "⏱️ Лобби распущено по таймеру.",
                )

    return expired_count


async def _send_simple_message(
    client: httpx.AsyncClient, chat_id: int, text_str: str,
) -> bool:
    """Минимальный sendMessage без кнопок и parse_mode. Для системных
    уведомлений где Markdown/HTML не нужен. Errors silenced."""
    if not BOT_TOKEN:
        return False
    try:
        r = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text_str, "disable_web_page_preview": True},
            timeout=5.0,
        )
        return r.status_code == 200
    except Exception as e:
        logger.warning("[tm_notifier] sendMessage chat_id=%s error: %s", chat_id, e)
        return False


async def run_loop() -> None:
    """Бесконечный цикл поллинга. Прерывается KeyboardInterrupt."""
    if not BOT_TOKEN:
        logger.error("[tm_notifier] BOT_TOKEN missing; refusing to start")
        return

    # Логируем DATABASE_URL — частая причина «молчания» — это запуск воркера
    # из неверной рабочей директории, когда фоллбэк sqlite:///./backend/...
    # резолвится в пустой файл, отличный от того, куда пишут api.py / bot.py.
    # Видя URL в логе, проблему ловишь с первой же строки.
    from backend.database import DATABASE_URL as _DB_URL

    logger.info(
        "[tm_notifier] started: delay=%dmin poll=%ds batch=%d miniapp_url=%s db=%s",
        REVIEW_DELAY_MINUTES,
        POLL_INTERVAL_SECONDS,
        BATCH_SIZE,
        MINI_APP_URL or "(none — buttons will be skipped)",
        _DB_URL,
    )

    cycle = 0
    while True:
        cycle += 1
        t0 = time.monotonic()
        n_reviews = 0
        n_lobbies = 0
        try:
            n_reviews = await process_pending_reviews()
        except Exception:
            # Никогда не валим цикл из-за разовой ошибки в SELECT/UPDATE/HTTP —
            # просто логируем и идём в следующий sleep.
            logger.exception("[tm_notifier] reviews cycle #%d failed", cycle)
        try:
            n_lobbies = await process_expired_lobbies()
        except Exception:
            logger.exception("[tm_notifier] lobbies cycle #%d failed", cycle)

        elapsed = time.monotonic() - t0
        # Heartbeat: лог КАЖДОГО цикла — иначе при пустой выборке (нормальный
        # рабочий случай) воркер молчит часами и кажется зависшим.
        logger.info(
            "[tm_notifier] cycle #%d: reviews=%d lobbies_expired=%d (%.2fs); "
            "next poll in %ds",
            cycle, n_reviews, n_lobbies, elapsed, POLL_INTERVAL_SECONDS,
        )
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_loop())
    except KeyboardInterrupt:
        logger.info("[tm_notifier] stopped by user")
