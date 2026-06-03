import aiosqlite

DATABASE_URL = "bot.db"

async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS moods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mood TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else "ru"

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)",
            (user_id, lang)
        )
        await db.commit()

async def save_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()

async def get_context(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        messages = await cursor.fetchall()
        return [{"role": msg[0], "content": msg[1]} for msg in reversed(messages)]

async def save_mood(user_id: int, mood: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("INSERT INTO moods (user_id, mood) VALUES (?, ?)", (user_id, mood))
        await db.commit()

async def get_mood_stats(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            async def get_last_interaction(user_id: int):
    """Получить время последнего сообщения"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT MAX(timestamp) FROM messages WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result[0] else None

async def update_last_interaction(user_id: int):
    """Обновить время последнего взаимодействия"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, last_seen) VALUES (?, datetime('now'))",
            (user_id,)
        )
        await db.commit()
            "SELECT mood, COUNT(*) as count FROM moods WHERE user_id = ? GROUP BY mood ORDER BY count DESC",
            (user_id,)
        )
        return await cursor.fetchall()
