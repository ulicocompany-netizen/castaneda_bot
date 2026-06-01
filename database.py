import aiosqlite
import asyncio
from datetime import datetime, timedelta

DB_PATH = "warrior_path.db"

async def init_db():
    """Создаём таблицы при запуске"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                sub_status TEXT DEFAULT 'free',
                sub_expires TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_history (
                user_id INTEGER,
                role TEXT,
                content TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    """Получаем язык пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM users WHERE id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else "ru"

async def set_user_lang(user_id: int, lang: str):
    """Сохраняем язык"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO users (id, lang) VALUES (?,?)", (user_id, lang))
        await db.commit()

async def save_message(user_id: int, role: str, content: str):
    """Сохраняем сообщение в историю"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?,?,?)", 
                        (user_id, role, content))
        # Храним только последние 10 сообщений
        await db.execute("""
            DELETE FROM chat_history 
            WHERE user_id=? AND rowid NOT IN (
                SELECT rowid FROM chat_history 
                WHERE user_id=? ORDER BY ts DESC LIMIT 10
            )
        """, (user_id, user_id))
        await db.commit()

async def get_context(user_id: int) -> list:
    """Получаем контекст диалога"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role, content FROM chat_history WHERE user_id=? ORDER BY ts ASC", 
            (user_id,)
        ) as cur:
            return [{"role": r, "content": c} async for r, c in cur]