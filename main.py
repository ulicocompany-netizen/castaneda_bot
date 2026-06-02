import os
import asyncio
import datetime
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from dotenv import load_dotenv
from openai import AsyncOpenAI

from prompts import CASTANEDA_THERAPY_PROMPT
from database import (
    init_db, get_user_lang, set_user_lang, 
    save_message, get_context, save_mood
)
from keyboards import (
    get_language_keyboard, get_main_menu_keyboard, get_mood_keyboard,
    get_breathing_keyboard, get_emergency_keyboard, get_premium_sessions_keyboard
)
from payments import handle_subscribe

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Клиент для DeepSeek (основной мозг)
deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# Клиент для OpenAI (для распознавания голоса - Whisper)
openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# ============================================
# 🎨 ФУНКЦИЯ ОПРЕДЕЛЕНИЯ ВРЕМЕНИ СУТОК
# ============================================
def get_time_theme():
    hour = datetime.datetime.now().hour
    
    if 6 <= hour < 12:
        return {
            "emoji": "☀️",
            "greeting": "Доброе утро, воин",
            "description": "Солнце встаёт из-за горизонта. Новый день — новые возможности.",
            "color": "🌅",
            "photo_url": "https://i.ibb.co/wFdsNJgm/image.jpg"
        }
    elif 12 <= hour < 17:
        return {
            "emoji": "🌤️",
            "greeting": "Добрый день, путник",
            "description": "Солнце в зените. Время действия и силы.",
            "color": "☀️",
            "photo_url": "https://i.ibb.co/xK5b1SKR/1.jpg"
        }
    elif 17 <= hour < 22:
        return {
            "emoji": "🌆",
            "greeting": "Добрый вечер, странник",
            "description": "Солнце садится. Время размышлений и видения.",
            "color": "🌄",
            "photo_url": "https://i.ibb.co/fzCjhYXR/image.jpg"
        }
    else:
        return {
            "emoji": "🌙",
            "greeting": "Доброй ночи, видящий",
            "description": "Ночь наступила. Время снов и второго внимания.",
            "color": "✨",
            "photo_url": "https://i.ibb.co/MDS0D0Lv/image.jpg"
        }

# ============================================
# 💬 ГЛАВНАЯ ФУНКЦИЯ ОТВЕТА
# ============================================
async def process_text_message(message: types.Message, text: str):
    user_id = message.from_user.id
    context = await get_context(user_id)
    
    messages = [{"role": "system", "content": CASTANEDA_THERAPY_PROMPT}]
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
        await message.answer(" Мир зашумел... Подожди мгновение и попробуй снова.")
        print(f"DeepSeek Error: {e}")

# ============================================
#  КОМАНДА /start
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
    
    try:
        await message.answer_photo(
            photo=theme["photo_url"],
            caption=text,
            reply_markup=get_language_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Photo error: {e}")
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
        f"{theme['emoji']} Теперь используй /menu для выбора практики или просто напиши мне (можно голосом 🎤).",
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
# 🎯 ОБРАБОТКА КНОПОК МЕНЮ (практики)
# ============================================
@dp.callback_query(lambda c: c.data.startswith("session_"))
async def process_session(callback: CallbackQuery):
    session_type = callback.data.replace("session_", "")
    
    sessions = {
        "stop_world": "🌑 **Остановить мир**\n\nПрактика прерывания автоматизмов мышления.\nОпиши ситуацию, которая заела.",
        "death": "💀 **Разговор со смертью**\n\nСмерть стоит за твоим левым плечом...\nЧто бы ты сделал иначе, если бы знал, что это последний день?",
        "heart": "❤️ **Путь с сердцем**\n\nЕсть ли радость в том, что ты делаешь?\nИли лишь долг и страх?",
        "dreams": "🦅 **Видение снов**\n\nРасскажи свой сон. Мы посмотрим на него через призму второго внимания.",
        "intention": "⚡ **Намерение**\n\nСформулируй своё намерение. Не цель — а намерение. Почувствуй разницу."
    }
    
    text = sessions.get(session_type, "🤔 Выбери практику из меню")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ============================================
# 🎤 ОБРАБОТКА ГОЛОСОВЫХ СООБЩЕНИЙ
# ============================================
@dp.message(lambda message: message.voice)
async def handle_voice(message: types.Message):
    if not os.getenv("OPENAI_API_KEY"):
        await message.answer("🔇 Распознавание голоса недоступно. Напиши текстом.")
        return

    await message.answer("🎤 Слушаю тебя, воин...")
    
    try:
        file_info = await bot.get_file(message.voice.file_id)
        file_url = f'https://api.telegram.org/file/bot{os.getenv("TELEGRAM_TOKEN")}/{file_info.file_path}'
        response = requests.get(file_url)
        
        if response.status_code != 200:
            raise Exception("Failed to download voice file")

        transcription = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=("voice.ogg", response.content, "audio/ogg"),
            language="ru"
        )
        
        recognized_text = transcription.text
        print(f"Распознанный текст: {recognized_text}")
        
        await message.answer(
            f"📝 _Распознано: {recognized_text}_", 
            parse_mode="Markdown"
        )
        await process_text_message(message, recognized_text)
        
    except Exception as e:
        await message.answer(
            "🌫 Голос растворился в ветре. Не удалось распознать. Попробуй ещё раз или напиши текстом."
        )
        print(f"Whisper Error: {e}")

# ============================================
#  ОБРАБОТКА ОБЫЧНОГО ТЕКСТА
# ============================================
@dp.message()
async def handle_text(message: types.Message):
    if message.text:
        await process_text_message(message, message.text)

# ============================================
# 😊 ОБРАБОТКА НАСТРОЕНИЯ
# ============================================
@dp.callback_query(lambda c: c.data == "mood_check")
async def mood_check(callback: CallbackQuery):
    await callback.message.answer(
        "😊 **Как ты себя чувствуешь?**",
        reply_markup=get_mood_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("mood_") and c.data != "mood_check")
async def mood_select(callback: CallbackQuery):
    mood = callback.data.replace("mood_", "")
    user_id = callback.from_user.id
    
    await save_mood(user_id, mood)
    
    mood_responses = {
        "good": "😊 Рад, что у тебя всё хорошо! Воин сохраняет ясность в радости.",
        "ok": "😐 Нормально — это тоже путь. Воин не судит своё состояние.",
        "bad": "😔 Я слышу тебя. Иногда признать боль — первый шаг к исцелению. Расскажи, что случилось?",
        "anxiety": "😰 Тревога — это ветер, который пытается сбить тебя с пути. Но воин стоит твёрдо. Давай подышим вместе?"
    }
    
    text = mood_responses.get(mood, "Я понял тебя.")
    await callback.message.answer(text)
    await callback.answer()

# ============================================
# 🧘 ДЫХАТЕЛЬНЫЕ УПРАЖНЕНИЯ
# ============================================
@dp.callback_query(lambda c: c.data == "breathing")
async def breathing_menu(callback: CallbackQuery):
    await callback.message.answer(
        "🧘 **Выбери дыхательную практику:**\n\n"
        "🌊 **4-7-8** — расслабление и сон\n"
        "🌬️ **Равное дыхание** — баланс и спокойствие\n"
        "🔥 **Огненное дыхание** — энергия и бодрость",
        reply_markup=get_breathing_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("breathe_"))
async def breathing_exercise(callback: CallbackQuery):
    exercise = callback.data.replace("breathe_", "")
    
    exercises = {
        "478": (
            "🌊 **Техника 4-7-8**\n\n"
            "1. Вдох через нос — **4 секунды**\n"
            "2. Задержи дыхание — **7 секунд**\n"
            "3. Выдох через рот — **8 секунд**\n\n"
            "Повтори 4 раза. Идеально перед сном. 💤"
        ),
        "equal": (
            "🌬️ **Равное дыхание**\n\n"
            "1. Вдох — **4 секунды**\n"
            "2. Выдох — **4 секунды**\n\n"
            "Повтори 5-10 раз. Возвращает в настоящее мгновение. ⚖️"
        ),
        "fire": (
            " **Огненное дыхание**\n\n"
            "1. Резкий выдох через нос\n"
            "2. Вдох происходит автоматически\n"
            "3. Темп: 1-2 цикла в секунду\n\n"
            "Делай 30 секунд. Даёт мощный прилив энергии! ⚡"
        )
    }
    
    text = exercises.get(exercise, "Выбери упражнение из меню.")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ============================================
# 🆘 ЭКСТРЕННАЯ ПОМОЩЬ
# ============================================
@dp.callback_query(lambda c: c.data == "emergency")
async def emergency(callback: CallbackQuery):
    await callback.message.answer(
        "🆘 **Ты не один, воин.**\n\n"
        "📞 **Телефон доверия (Россия):** 8-800-2000-122 (бесплатно)\n\n"
        "Если тебе сейчас очень плохо — позвони. Это не слабость, это мудрость.\n\n"
        "🧘 Или попробуй быструю технику самопомощи:",
        reply_markup=get_emergency_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "emergency_help")
async def emergency_help(callback: CallbackQuery):
    await callback.message.answer(
        "🧘 **Быстрая техника заземления 5-4-3-2-1:**\n\n"
        "👀 Назови **5 вещей**, которые ты видишь\n"
        "👂 **4 звука**, которые слышишь\n"
        "✋ **3 ощущения** в теле\n"
        "👃 **2 запаха**\n"
        "👅 **1 вкус**\n\n"
        "Это возвращает в настоящее. Ты здесь. Ты в безопасности. 🌿"
    )
    await callback.answer()

# ============================================
# 🔙 НАЗАД В МЕНЮ
# ============================================
@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    theme = get_time_theme()
    await callback.message.answer(
        f"{theme['emoji']} **Главное меню:**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ============================================
# 💳 ПОДПИСКА
# ============================================
@dp.callback_query(lambda c: c.data == "premium_sessions")
async def process_premium(callback: CallbackQuery):
    await callback.message.answer(
        "🔒 **Premium-сессии**\n\n"
        "🦅 Видение снов\n"
        "⚡ Намерение\n"
        "🗺️ Карта пути\n\n"
        "Доступно по подписке. Оформить?",
        reply_markup=get_premium_sessions_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "subscribe")
async def process_subscribe(callback: CallbackQuery):
    await handle_subscribe(callback)

# ============================================
# 🚀 ЗАПУСК БОТА
# ============================================
async def main():
    await init_db()
    print("🪶 Бот запущен и готов к пути воина...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
