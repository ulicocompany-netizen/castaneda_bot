# ============================================
# ANALYTICS.PY — АНАЛИТИКА БОТА + /stats
# ============================================
import aiosqlite
from datetime import datetime
from aiogram import types
from aiogram.filters import Command

DB_PATH = "bot.db"
YOUR_ID = 862373702
_ready = False

async def ensure():
    global _ready
    if _ready:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS analytics (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, type TEXT, event TEXT)")
        await db.commit()
    _ready = True

async def log(user_id, etype, event):
    try:
        await ensure()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO analytics (user_id, date, type, event) VALUES (?,?,?,?)", (user_id, datetime.now().isoformat(), etype, event))
            await db.commit()
    except Exception as e:
        print(f"❌ ANALYTICS: {e}")

def register_analytics(dp):
    @dp.message.outer_middleware()
    async def log_msg(handler, event, data):
        try:
            await log(event.from_user.id, "msg", (event.text or "media")[:50])
        except Exception:
            pass
        return await handler(event, data)

    @dp.callback_query.outer_middleware()
    async def log_cb(handler, event, data):
        try:
            await log(event.from_user.id, "btn", (event.data or "")[:50])
        except Exception:
            pass
        return await handler(event, data)

    @dp.message(Command("stats"))
    async def stats(message: types.Message):
        if message.from_user.id != YOUR_ID:
            return
        await ensure()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            users = (await (await db.execute("SELECT COUNT(DISTINCT user_id) c FROM analytics")).fetchone())["c"]
            ru = (await (await db.execute("SELECT COUNT(DISTINCT user_id) c FROM analytics WHERE event='lang_ru'")).fetchone())["c"]
            en = (await (await db.execute("SELECT COUNT(DISTINCT user_id) c FROM analytics WHERE event='lang_en'")).fetchone())["c"]
            rows = await (await db.execute("SELECT event, COUNT(*) c FROM analytics WHERE type='btn' GROUP BY event ORDER BY c DESC LIMIT 15")).fetchall()
        lines = [f"📊 АНАЛИТИКА\n\n👥 Уникальных пользователей: {users}", f"🇷🇺 RU: {ru} · 🇬🇧 EN: {en}", "", "🔘 Кнопки (топ-15):"]
        for r in rows:
            lines.append(f"{r['event']}: {r['c']}")
        await message.answer("\n".join(lines))

async def get_media_file_id(key):
    await ensure()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS media_cache (key TEXT PRIMARY KEY, file_id TEXT)")
        cur = await db.execute("SELECT file_id FROM media_cache WHERE key=?", (key,))
        row = await cur.fetchone()
    return row[0] if row else None

async def set_media_file_id(key, file_id):
    await ensure()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS media_cache (key TEXT PRIMARY KEY, file_id TEXT)")
        await db.execute("INSERT OR REPLACE INTO media_cache (key, file_id) VALUES (?,?)", (key, file_id))
        await db.commit()