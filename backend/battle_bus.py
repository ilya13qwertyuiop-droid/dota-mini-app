"""battle_bus.py — межворкерная шина событий «Битвы драфтов».

Архитектура (см. анализ транспорта в проекте): состояние битвы живёт в PG,
long-poll клиенты висят на локальных asyncio.Event своего воркера, а о
изменениях, записанных ЧЕРЕЗ ДРУГОЙ воркер, узнают по PG NOTIFY:

    действие игрока → COMMIT → pg_notify('draft_battle', battle_id)
        → listener-поток каждого воркера → loop.call_soon_threadsafe
        → fire_local(battle_id) → asyncio.Event.set() → ответ long-poll'у.

На dev-SQLite NOTIFY не существует — но dev-uvicorn однопроцессный, поэтому
fire_local в notify_battle_changed() покрывает доставку полностью.

Надёжность: listener-поток переподключается с backoff. Events-эндпоинт после
первого чтения регистрирует waiter, контрольный раз перечитывает state_version
и только потом засыпает. Поэтому изменение не теряется на границе read/await;
при реконнекте худший исход деградации — +таймаут удержания к латентности.
"""

from __future__ import annotations

import asyncio
import logging
import select
import threading
import time

from backend.database import DATABASE_URL

logger = logging.getLogger(__name__)

_CHANNEL = "draft_battle"
_IS_PG = DATABASE_URL.startswith("postgresql")

# battle_id -> set[asyncio.Event] ожидающих long-poll'ов ЭТОГО воркера.
_waiters: dict[int, set[asyncio.Event]] = {}
_waiters_lock = threading.Lock()

# event loop воркера — захватывается при первом ожидании; нужен listener-потоку
# для threadsafe-проброса событий.
_loop: asyncio.AbstractEventLoop | None = None

_listener_started = False
_listener_start_lock = threading.Lock()


class BattleChangeSubscription:
    """Зарегистрированное ожидание изменения одной битвы.

    Подписка создаётся ДО контрольного перечитывания state_version. Поэтому
    уведомление, пришедшее между перечитыванием БД и фактическим ``await``, уже
    поставит Event и не потеряется. ``close`` идемпотентен: endpoint вызывает
    его из ``finally`` и при отмене long-poll клиентом утечки waiters нет.
    """

    def __init__(self, battle_id: int, event: asyncio.Event) -> None:
        self.battle_id = int(battle_id)
        self._event = event
        self._closed = False

    async def wait(self, timeout: float) -> bool:
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with _waiters_lock:
            bucket = _waiters.get(self.battle_id)
            if bucket is not None:
                bucket.discard(self._event)
                if not bucket:
                    _waiters.pop(self.battle_id, None)


def subscribe_to_changes(battle_id: int) -> BattleChangeSubscription:
    """Регистрирует waiter немедленно и возвращает управляемую подписку."""
    global _loop
    _loop = asyncio.get_running_loop()
    _ensure_listener()

    event = asyncio.Event()
    battle_id = int(battle_id)
    with _waiters_lock:
        _waiters.setdefault(battle_id, set()).add(event)
    return BattleChangeSubscription(battle_id, event)


def fire_local(battle_id: int) -> None:
    """Будит всех локальных ожидающих битвы. Только из event loop-потока
    (listener зовёт через call_soon_threadsafe)."""
    with _waiters_lock:
        events = list(_waiters.get(battle_id) or ())
    for ev in events:
        ev.set()


def _fire_threadsafe(battle_id: int) -> None:
    if _loop is not None and not _loop.is_closed():
        _loop.call_soon_threadsafe(fire_local, battle_id)


def notify_battle_changed(battle_id: int) -> None:
    """Зовётся ПОСЛЕ commit'а любого изменения битвы.

    PG: pg_notify — доставка во все воркеры (включая свой: его listener тоже
    подписан, но локальный fire ниже даёт нулевую латентность своим клиентам).
    SQLite/dev: только локальный fire (один процесс — этого достаточно).
    """
    if _IS_PG:
        try:
            from sqlalchemy import text
            from backend.database import engine
            with engine.connect() as conn:
                conn.execute(
                    text("SELECT pg_notify(:ch, :payload)"),
                    {"ch": _CHANNEL, "payload": str(int(battle_id))},
                )
                conn.commit()
        except Exception as e:
            # Шина — про латентность, не про корректность: ожидающие всё равно
            # дочитают изменение по таймауту удержания (версия в БД уже новая).
            logger.warning("[battle_bus] pg_notify failed: %s", e)
    # Свой воркер — мгновенно и без сети. Если зовётся из threadpool-треда
    # (def-эндпоинты), пробрасываем в loop threadsafe.
    if _loop is not None:
        _fire_threadsafe(battle_id)


async def wait_for_change(battle_id: int, timeout: float) -> bool:
    """Висит до сигнала об изменении битвы или таймаута. True = был сигнал.

    Регистрирует одноразовый Event; снятие — в finally, утечек при отмене
    запроса (клиент ушёл) нет. Также лениво запускает listener и захватывает
    loop при первом использовании.
    """
    subscription = subscribe_to_changes(battle_id)
    try:
        return await subscription.wait(timeout)
    finally:
        subscription.close()


def _ensure_listener() -> None:
    """Однократный запуск LISTEN-потока (только PG)."""
    global _listener_started
    if not _IS_PG or _listener_started:
        return
    with _listener_start_lock:
        if _listener_started:
            return
        t = threading.Thread(
            target=_listen_loop, name="battle-bus-listener", daemon=True
        )
        t.start()
        _listener_started = True
        logger.info("[battle_bus] LISTEN thread started (channel=%s)", _CHANNEL)


def _listen_loop() -> None:
    """Выделенное соединение (ВНЕ пула SQLAlchemy) + LISTEN + select-цикл.

    Внешний while — реконнект с backoff: упавшее соединение не убивает шину,
    лишь временно деградирует латентность до таймаута удержания long-poll'а.
    """
    import psycopg2

    backoff = 1.0
    while True:
        conn = None
        try:
            # SQLAlchemy-URL → DSN психопга: отрезаем диалект-суффикс.
            dsn = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://", 1)
            conn = psycopg2.connect(dsn)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            with conn.cursor() as cur:
                cur.execute(f"LISTEN {_CHANNEL}")
            logger.info("[battle_bus] listening on %s", _CHANNEL)
            backoff = 1.0
            while True:
                # 10с select-таймаут — живой цикл, который заметит разрыв.
                if select.select([conn], [], [], 10.0) == ([], [], []):
                    continue
                conn.poll()
                while conn.notifies:
                    n = conn.notifies.pop(0)
                    try:
                        _fire_threadsafe(int(n.payload))
                    except (TypeError, ValueError):
                        logger.warning("[battle_bus] bad payload: %r", n.payload)
        except Exception as e:
            logger.warning(
                "[battle_bus] listener error: %s — reconnect in %.0fs", e, backoff
            )
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
