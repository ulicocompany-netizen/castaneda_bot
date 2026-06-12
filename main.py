import os
import asyncio
import datetime
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from dotenv import load_dotenv
from openai import AsyncOpenAI
from datetime import datetime, timedelta, timezone

from prompts import CASTANEDA_THERAPY_PROMPT
from database import (
    init_db, get_user_lang, set_user_lang, 
    save_message, get_context, save_mood,
    get_last_interaction, update_last_interaction,
    is_subscribed, set_subscription, get_subscription_status,
    get_users_without_subscription, get_last_reminder, update_last_reminder,
    get_messages_today, increment_messages_today,
    delete_user_data
)
from keyboards import (
    get_language_keyboard, get_main_menu_keyboard, get_mood_keyboard,
    get_breathing_keyboard, get_consultation_keyboard,
    get_documents_keyboard, get_age_keyboard,
    get_subscription_keyboard, get_payment_keyboard
)
from documents import (
    POLICY_RU, TERMS_RU, OFFER_RU,
    POLICY_EN, TERMS_EN, OFFER_EN
)
from reminders import get_random_reminder, should_send_reminder

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

YOUR_ID = 862373702
FREE_MESSAGES_LIMIT = 5

# Ссылка на приветственное видео
INTRO_VIDEO_URL = "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/refs/heads/main/10%20%D0%BC%D0%B1.mp4"

def get_time_theme():
    utc_now = datetime.now(timezone.utc)
    moscow_tz = timezone(timedelta(hours=3))
    moscow_time = utc_now.astimezone(moscow_tz)
    hour = moscow_time.hour
    
    if 6 <= hour < 12:
        return {
            "emoji": "☀️",
            "greeting": "Доброе утро, воин",
            "description": "Солнце встаёт из-за горизонта. Новый день — новые возможности.",
            "color": "🌅",
            "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/утро.jpeg"
        }
    elif 12 <= hour < 17:
        return {
            "emoji": "🌤️",
            "greeting": "Добрый день, путник",
            "description": "Солнце в зените. Время действия и силы.",
            "color": "☀️",
            "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/день1.jpeg"
        }
    elif 17 <= hour < 22:
        return {
            "emoji": "🌆",
            "greeting": "Добрый вечер, странник",
            "description": "Солнце садится. Время размышлений и видения.",
            "color": "🌄",
            "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/сумерки.jpeg"
        }
    else:
        return {
            "emoji": "🌙",
            "greeting": "Доброй ночи, видящий",
            "description": "Ночь наступила. Время снов и второго внимания.",
            "color": "✨",
            "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/ночь.jpeg"
        }

async def process_text_message(message: types.Message, text: str):
    user_id = message.from_user.id
    context = await get_context(user_id)
    user_lang = await get_user_lang(user_id)
    
    if user_lang == "ru":
        lang_instruction = "\n\n🔴 ВАЖНОЕ ПРАВИЛО:\n- Пользователь пишет на РУССКОМ языке\n- Ты ДОЛЖЕН отвечать ТОЛЬКО на РУССКОМ\n- НИКАКОГО английского в ответах"
    else:
        lang_instruction = "\n\n🔴 IMPORTANT RULE:\n- User writes in ENGLISH\n- You MUST respond ONLY in ENGLISH\n- NO Russian in your answers"
    
    system_prompt = CASTANEDA_THERAPY_PROMPT + lang_instruction
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(context)
    messages.append({"role": "user", "content": text})
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.75,
            max_tokens=600
        )
        reply = response.choices[0].message.content
        await save_message(user_id, "user", text)
        await save_message(user_id, "assistant", reply)
        await message.answer(reply)
    except Exception as e:
        await message.answer("🌫 Мир зашумел... Подожди мгновение и попробуй снова.")
        print(f"DeepSeek Error: {e}")

async def check_and_greet_if_needed(message: types.Message):
    user_id = message.from_user.id
    last_interaction = await get_last_interaction(user_id)
    
    if last_interaction is None:
        return True
    
    try:
        last_time = datetime.fromisoformat(last_interaction.replace('Z', '+00:00').replace('+00:00', ''))
        now = datetime.now()
        hours_diff = (now - last_time).total_seconds() / 3600
        is_new_day = now.date() != last_time.date()
        return hours_diff > 12 or is_new_day
    except:
        return False

async def check_message_limit(user_id: int) -> bool:
    if await is_subscribed(user_id):
        return True
    messages_count = await get_messages_today(user_id)
    return messages_count < FREE_MESSAGES_LIMIT

async def send_limit_message(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    
    text_ru = (
        "⚠️ **Ты достиг дневного лимита**\n\n"
        f"Бесплатно доступно {FREE_MESSAGES_LIMIT} сообщений в день.\n\n"
        "🌟 **Оформи подписку** — и путь откроется полностью:\n"
        "• Безлимитные сообщения\n"
        "• 🦅 Видение снов\n"
        "• ⚡ Работа с намерением\n"
        "• 💬 Личная поддержка\n\n"
        "→ /subscribe"
    )
    
    text_en = (
        "⚠️ **You've reached the daily limit**\n\n"
        f"Free version allows {FREE_MESSAGES_LIMIT} messages per day.\n\n"
        "🌟 **Subscribe** — and the path opens fully:\n"
        "• Unlimited messages\n"
        "• 🦅 Dreaming\n"
        "• ⚡ Working with intention\n"
        "• 💬 Personal support\n\n"
        "→ /subscribe"
    )
    
    text = text_en if user_lang == "en" else text_ru
    await message.answer(text, parse_mode="Markdown")

# ============================================
# 🚀 ВСЕ КОМАНДЫ СНАЧАЛА (ПОРЯДОК ВАЖЕН!)
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    context = await get_context(user_id)
    age_confirmed = any(msg["content"] == "age_confirmed" for msg in context if msg["role"] == "system")
    
    if age_confirmed:
        theme = get_time_theme()
        user_lang = await get_user_lang(user_id)
        
        text = (
            f"{theme['emoji']} **{theme['greeting']}**\n\n"
            f"{theme['description']}\n\n"
            f"🪶 Рад видеть тебя снова, воин."
        )
        
        try:
            await message.answer_photo(
                photo=theme["photo_url"],
                caption=text,
                reply_markup=get_main_menu_keyboard(user_lang),
                parse_mode="Markdown"
            )
        except:
            await message.answer(text, reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")
    else:
        user_lang = await get_user_lang(user_id)
        theme = get_time_theme()
        
        text_ru = (
            f"🦅 **ПЕРЕСТУПИТЬ ПОРОГ**\n\n"
            f"{theme['emoji']} *{theme['greeting']}*\n\n"
            "Путь воина — не для детей.\n"
            "Он требует зрелости, смелости и готовности\n"
            "встретиться с собой настоящим.\n\n"
            "Здесь ты найдёшь:\n"
            "• Разговоры со смертью\n"
            "• Остановку внутреннего диалога\n"
            "• Практики второго внимания\n\n"
            "⚠️ Этот путь — для тех, кому есть 18.\n\n"
            "**Готов ли ты переступить порог?**"
        )
        
        text_en = (
            f"🦅 **CROSS THE THRESHOLD**\n\n"
            f"{theme['emoji']} *{theme['greeting']}*\n\n"
            "The warrior's path is not for children.\n"
            "It requires maturity, courage, and readiness\n"
            "to meet your true self.\n\n"
            "Here you will find:\n"
            "• Conversations with death\n"
            "•
