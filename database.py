import aiosqlite
from datetime import datetime, timedelta

DATABASE_URL = "bot.db"

async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        # Основная таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                subscription_end DATETIME,
                last_seen DATETIME,
                last_reminder DATETIME,
                messages_today INTEGER DEFAULT 0,
                last_message_date TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                tale1_seen INTEGER DEFAULT 0
            )
        """)
        
        # Таблица сообщений (контекст диалога)
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
        
        # Таблица настроений
        await db.execute("""
            CREATE TABLE IF NOT EXISTS moods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mood TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица для FSM сказки (текущий шаг)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_fsm (
                user_id INTEGER PRIMARY KEY,
                tale_step INTEGER DEFAULT 0
            )
        """)
        
        # Таблица событий воронки сказки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fable_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event TEXT,
                timestamp TEXT
            )
        """)
        
        await db.commit()

# ============================================
# ЯЗЫК ПОЛЬЗОВАТЕЛЯ
# ============================================

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

# ============================================
# СООБЩЕНИЯ И КОНТЕКСТ
# ============================================

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

# ============================================
# НАСТРОЕНИЯ
# ============================================

async def save_mood(user_id: int, mood: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("INSERT INTO moods (user_id, mood) VALUES (?, ?)", (user_id, mood))
        await db.commit()

async def get_mood_stats(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT mood, COUNT(*) as count FROM moods WHERE user_id = ? GROUP BY mood ORDER BY count DESC",
            (user_id,)
        )
        return await cursor.fetchall()

# ============================================
# ПОСЛЕДНЕЕ ВЗАИМОДЕЙСТВИЕ
# ============================================

async def get_last_interaction(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT MAX(timestamp) FROM messages WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result[0] else None

async def update_last_interaction(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, last_seen) VALUES (?, datetime('now'))",
            (user_id,)
        )
        await db.commit()

# ============================================
# ПОДПИСКА
# ============================================

async def get_subscription_status(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None

async def set_subscription(user_id: int, days: int = 30):
    end_date = datetime.now() + timedelta(days=days)
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET subscription_end = ? WHERE user_id = ?",
            (end_date.isoformat(), user_id)
        )
        await db.commit()

async def is_subscribed(user_id: int) -> bool:
    # Админ (ты) всегда имеет доступ ко всему
    if user_id == 862373702:
        return True
    
    sub_end = await get_subscription_status(user_id)
    if not sub_end:
        return False
    try:
        end_date = datetime.fromisoformat(sub_end)
        return datetime.now() < end_date
    except:
        return False

async def get_users_without_subscription():
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute("""
            SELECT user_id, last_seen FROM users 
            WHERE subscription_end IS NULL OR subscription_end < ?
        """, (datetime.now().isoformat(),))
        return await cursor.fetchall()

# ============================================
# НАПОМИНАНИЯ
# ============================================

async def update_last_reminder(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET last_reminder = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        await db.commit()

async def get_last_reminder(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT last_reminder FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None

# ============================================
# ЛИМИТЫ СООБЩЕНИЙ
# ============================================

async def get_messages_today(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT messages_today, last_message_date FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        if not result:
            return 0
        
        messages_count, last_date = result
        today = datetime.now().strftime("%Y-%m-%d")
        
        if last_date != today:
            return 0
        return messages_count or 0

async def increment_messages_today(user_id: int):
    # Админ не тратит лимит
    if user_id == 862373702:
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT last_message_date FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        
        if not result or result[0] != today:
            await db.execute(
                "UPDATE users SET messages_today = 1, last_message_date = ? WHERE user_id = ?",
                (today, user_id)
            )
        else:
            await db.execute(
                "UPDATE users SET messages_today = messages_today + 1 WHERE user_id = ?",
                (user_id,)
            )
        await db.commit()

# ============================================
# УДАЛЕНИЕ ДАННЫХ
# ============================================

async def delete_user_data(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM moods WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM user_fsm WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM fable_events WHERE user_id = ?", (user_id,))
        await db.execute(
            "UPDATE users SET tale1_seen = 0, messages_today = 0, "
            "last_message_date = NULL, subscription_end = NULL, "
            "last_seen = NULL, last_reminder = NULL WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

# ============================================
# СКАЗКА: FSM И ЛОГИРОВАНИЕ ВОРОНКИ
# ============================================

async def set_tale_step(user_id: int, step: int):
    """Сохранить текущий шаг сказки"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_fsm (user_id, tale_step) VALUES (?, ?)",
            (user_id, step)
        )
        await db.commit()

async def get_tale_step(user_id: int) -> int:
    """Получить текущий шаг сказки"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        async with db.execute(
            "SELECT tale_step FROM user_fsm WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def set_tale1_seen(user_id: int):
    """Отметить, что пользователь видел сказку 1"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET tale1_seen = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

async def is_tale1_seen(user_id: int) -> bool:
    """Проверить, видел ли пользователь сказку 1"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        async with db.execute(
            "SELECT tale1_seen FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0])

async def log_fable_event(user_id: int, event: str):
    """Записать событие воронки сказки"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO fable_events (user_id, event, timestamp) VALUES (?, ?, ?)",
            (user_id, event, datetime.now().isoformat())
        )
        await db.commit()