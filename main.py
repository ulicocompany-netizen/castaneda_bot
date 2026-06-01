import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from dotenv import load_dotenv
from openai import AsyncOpenAI

from prompts import CASTANEDA_THERAPY_PROMPT
from database import init_db, get_user_lang, set_user_lang, save_message, get_context
from keyboards import get_language_keyboard, get_main_menu_keyboard, get_premium_sessions_keyboard
from payments import handle_subscribe

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# ============================================
# 🎨 ФУНКЦИЯ ОПРЕДЕЛЕНИЯ ВРЕМЕНИ СУТОК
# ============================================
def get_time_theme():
    """Возвращает тему и картинку в зависимости от времени"""
    hour = datetime.datetime.now().hour
    
    if 6 <= hour < 12:
        # ☀️ УТРО (6:00 - 12:00)
        return {
            "emoji": "☀️",
            "greeting": "Доброе утро, воин",
            "description": "Солнце встаёт из-за горизонта. Новый день — новые возможности.",
            "color": "🌅",
            # 👇 ЗАМЕНИ ССЫЛКУ НИЖЕ НА СВОЮ КАРТИНКУ (утро/рассвет)
            "photo_url": "https://ibb.co/7dS4JgCm"  
        }
    elif 12 <= hour < 17:
        # 🌤️ ДЕНЬ (12:00 - 17:00)
        return {
            "emoji": "🌤️",
            "greeting": "Добрый день, путник",
            "description": "Солнце в зените. Время действия и силы.",
            "color": "☀️",
            # 👇 ЗАМЕНИ ССЫЛКУ НИЖЕ НА СВОЮ КАРТИНКУ (день/яркое солнце)
            "photo_url": "https://ibb.co/ymsC6nmb"  
        }
    elif 17 <= hour < 22:
        # 🌆 ВЕЧЕР (17:00 - 22:00)
        return {
            "emoji": "🌆",
            "greeting": "Добрый вечер, странник",
            "description": "Солнце садится. Время размышлений и видения.",
            "color": "🌄",
            # 👇 ЗАМЕНИ ССЫЛКУ НИЖЕ НА СВОЮ КАРТИНКУ (закат/вечер)
            "photo_url": "https://ibb.co/q3RTtMDG"  
        }
    else:
        # 🌙 НОЧЬ (22:00 - 6:00)
        return {
            "emoji": "🌙",
            "greeting": "Доброй ночи, видящий",
            "description": "Ночь наступила. Время снов и второго внимания.",
            "color": "✨",
            # 👇 ЗАМЕНИ ССЫЛКУ НИЖЕ НА СВОЮ КАРТИНКУ (ночь/звёзды)
            "photo_url": "https://ibb.co/HD4ND8QS"  
        }

# ============================================
# 🚀 КОМАНДА /start
# ============================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    theme = get_time_theme()
    
    text = (
        f"{theme['emoji']} **{theme['greeting']}**\n\n"
        f"{theme['description']}\n\n"
        f"🪶 Добро пожаловать на путь воина.\n\n"
        f"{theme['color']} Мир — лишь описание. Готов ли ты его остановить?\n\n"
        f"Выбери язык общения:"
    )
    
    # Отправляем с картинкой
    try:
        await message.answer_photo(
            photo=theme["photo_url"],
            caption=text,
            reply_markup=get_language_keyboard(),
            parse_mode="Markdown"
        )
    except:
        # Если картинка не загрузилась — просто текст
        await message.answer(
            text,
            reply_markup=get_language_keyboard(),
            parse_mode="Markdown"
        )

# ============================================
# 🌐 ВЫБОР ЯЗЫКА
# ============================================
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def process_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    await set_user_lang(user_id, lang)
    
    theme = get_time_theme()
    lang_names = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
    
    await callback.message.answer(
        f"✅ Язык установлен: {lang_names.get(lang, lang)}\n\n"
        f"{theme['emoji']} Теперь используй /menu для выбора практики.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

# ============================================
# 📋 КОМАНДА /menu
# ============================================
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    theme = get_time_theme()
    await message.answer(
        f"{theme['emoji']} **Выбери практику:**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ============================================
# 🎯 ОБРАБОТКА КНОПОК МЕНЮ
# ============================================
@dp.callback_query(lambda c: c.data.startswith("session_"))
async def process_session(callback: CallbackQuery):
    session_type = callback.data.replace("session_", "")
    
    sessions = {
        "stop_world": "🌑 **Остановить мир**\n\nПрактика прерывания автоматизмов мышления.\nОпиши ситуацию, которая заела.",
        "death": "💀 **Разговор со смертью**\n\nСмерть стоит за твоим левым плечом...\nЧто бы ты сделал иначе, если бы знал, что это последний день?",
        "heart": "❤️ **Путь с сердцем**\n\nЕсть ли радость в том, что ты делаешь?\nИли лишь долг и страх?",
        "dreams": "🦅 **Видение снов**\n\nРасскажи свой сон. Мы посмотрим на него через призму второго внимания.",
        "
