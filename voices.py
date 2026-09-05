# ============================================
# VOICES.PY — ГОЛОСОВЫЕ ВОРОНА (1 в день)
# ============================================
import os
import random
import aiosqlite
from datetime import datetime
from database import get_user_lang
from database import get_user_lang

DB_PATH = "bot.db"
VOICES_DIR = "voices"

# Номер триггера = папка «Триггер N ...» внутри voices
TRIGGER_NUM = {
    "practice": 1,
    "stop_world": 2,
    "indulgi": 3,
    "click": 4,
    "diagnose": 5,
    "magic": 6,
    "diary": 7,
    "universal": 8,
}

# Индульгиметр: какой файл в папке 3 под какой балл
INDULGI_FILE = {"low": "2", "mid": "1", "high": "3"}

AUDIO_EXT = (".mp3", ".ogg", ".oga")

async def _ensure():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS voice_log (user_id INTEGER PRIMARY KEY, last_date TEXT)")
        await db.commit()

async def _can_send(user_id):
    await _ensure()
    today = datetime.now().date().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_date FROM voice_log WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
    return not (row and row[0] == today)

async def _mark(user_id):
    today = datetime.now().date().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO voice_log (user_id, last_date) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET last_date=?", (user_id, today, today))
        await db.commit()

async def reset_voice_limit(user_id):
    """Сброс лимита для твоих тестов (команда /vtest)"""
    await _ensure()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM voice_log WHERE user_id=?", (user_id,))
        await db.commit()

def _trigger_folder(num):
    if not os.path.isdir(VOICES_DIR):
        return None
    for name in os.listdir(VOICES_DIR):
        path = os.path.join(VOICES_DIR, name)
        if os.path.isdir(path) and name.startswith(f"Триггер {num}"):
            return path
    return None

def _audio_files(folder):
    return [f for f in os.listdir(folder) if f.lower().endswith(AUDIO_EXT)]

async def send_raven_voice(bot, user_id, trigger):
    """Одно голосовое в день по триггеру. Если файла нет — молча пропускает."""
    try:
        if await get_user_lang(user_id) == "en":
            return
        if not await _can_send(user_id):
            return
        level = None
        if trigger.startswith("indulgi_"):
            level = trigger.replace("indulgi_", "")
            key = "indulgi"
        else:
            key = trigger
        folder = _trigger_folder(TRIGGER_NUM.get(key, 8))
        if not folder:
            return
        files = _audio_files(folder)
        if not files:
            return
        path = None
        if level:
            want = INDULGI_FILE.get(level, "")
            for f in files:
                if f.split(".")[0].strip() == want:
                    path = os.path.join(folder, f)
                    break
        if not path:
            path = os.path.join(folder, random.choice(files))
        from aiogram.types import FSInputFile
        await bot.send_voice(user_id, FSInputFile(path))
        await _mark(user_id)
    except Exception as e:
        print(f"❌ ОШИБКА ГОЛОСОВОГО [{trigger}]: {e}")