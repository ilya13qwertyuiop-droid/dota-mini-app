import sqlite3
from datetime import datetime, timedelta
import secrets
from pathlib import Path

DB_PATH = Path(__file__).parent / "dota_bot.db"  # используем существующую БД

def init_tokens_table():
    """Создаёт таблицу tokens, если её нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_token_for_user(user_id: int) -> str:
    """Генерирует токен и сохраняет в БД"""
    token = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    
    print(f"[DB DEBUG] Created token for user {user_id}: {token[:10]}...")
    return token

def get_user_id_by_token(token: str) -> int | None:
    """Проверяет токен и возвращает user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, expires_at FROM tokens WHERE token = ?",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"[DB DEBUG] Token not found: {token[:10]}...")
        return None
    
    user_id, expires_at_str = row
    expires_at = datetime.fromisoformat(expires_at_str)
    
    if expires_at < datetime.utcnow():
        print(f"[DB DEBUG] Token expired for user {user_id}")
        delete_token(token)
        return None
    
    print(f"[DB DEBUG] Token valid for user {user_id}")
    return user_id

def delete_token(token: str):
    """Удаляет просроченный токен"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ========== Hero matchups cache ==========

def init_hero_matchups_cache_table():
    """Создаёт таблицу hero_matchups_cache, если её нет."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hero_matchups_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hero_id INTEGER NOT NULL,
            opponent_hero_id INTEGER NOT NULL,
            games INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            winrate REAL NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(hero_id, opponent_hero_id)
        )
    """)
    conn.commit()
    conn.close()


def get_hero_matchups_from_cache(hero_id: int) -> tuple[list[dict], str | None]:
    """Читает матчапы героя из кэша.

    Возвращает:
        - список словарей {opponent_hero_id, games, wins, winrate, updated_at}
        - максимальный updated_at для данного hero_id (или None, если записей нет)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT opponent_hero_id, games, wins, winrate, updated_at
        FROM hero_matchups_cache
        WHERE hero_id = ?
        """,
        (hero_id,),
    )
    rows = cursor.fetchall()

    last_updated: str | None = None
    if rows:
        cursor.execute(
            "SELECT MAX(updated_at) FROM hero_matchups_cache WHERE hero_id = ?",
            (hero_id,),
        )
        last_updated = cursor.fetchone()[0]

    conn.close()

    matchups = [
        {
            "opponent_hero_id": row[0],
            "games": row[1],
            "wins": row[2],
            "winrate": row[3],
            "updated_at": row[4],
        }
        for row in rows
    ]
    return matchups, last_updated


def replace_hero_matchups_in_cache(
    hero_id: int, matchups: list[dict], updated_at: str
) -> None:
    """Атомарно заменяет матчапы героя в кэше.

    Удаляет все старые строки hero_id и вставляет новые в одной транзакции.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM hero_matchups_cache WHERE hero_id = ?", (hero_id,)
        )
        cursor.executemany(
            """
            INSERT INTO hero_matchups_cache
                (hero_id, opponent_hero_id, games, wins, winrate, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    hero_id,
                    m["opponent_hero_id"],
                    m["games"],
                    m["wins"],
                    m["winrate"],
                    updated_at,
                )
                for m in matchups
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
