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
