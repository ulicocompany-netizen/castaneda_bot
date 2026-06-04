import os
import asyncio
import datetime
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from dotenv import load_dotenv
from openai import AsyncOpenAI
from datetime import datetime, timedelta

from prompts import CASTANEDA_THERAPY_PROMPT
from database import (
    init_db, get_user_lang, set_user_lang, 
    save_message, get_context, save_mood,
    get_last_interaction
)
from keyboards import (
    get_language_keyboard, get_main_menu_keyboard, get_mood_keyboard,
    get_breathing_keyboard, get_consultation_keyboard, get_premium_sessions_keyboard
)
from payments import handle_subscribe

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

def get_time_theme():
    # Используем московское время (UTC+3)
    from datetime import timezone, timedelta
    
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
            "photo_url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800"
        }
    elif 12 <= hour < 17:
        return {
            "emoji": "🌤️",
            "greeting": "Добрый день, путник",
            "description": "Солнце в зените. Время действия и силы.",
            "color": "☀️",
            "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800"
        }
    elif 17 <= hour < 22:
        return {
            "emoji": "🌆",
            "greeting": "Добрый вечер, странник",
            "description": "Солнце садится. Время размышлений и видения.",
            "color": "🌄",
            "photo_url": "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800"
        }
    else:
        return {
            "emoji": "🌙",
            "greeting": "Доброй ночи, видящий",
            "description": "Ночь наступила. Время снов и второго внимания.",
            "color": "✨",
            "photo_url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800"
        }

async def process_text_message(message: types.Message, text: str):
    user_id = message.from_user.id
    context = await get_context(user_id)
    user_lang = await get_user_lang(user_id)
    
    lang_instruction = (
        "ОТВЕЧАЙ СТРОГО НА РУССКОМ ЯЗЫКЕ." if user_lang == "ru" 
        else "RESPOND STRICTLY IN ENGLISH. Do not use Russian."
    )
    
    system_prompt = CASTANEDA_THERAPY_PROMPT + "\n\n" + lang_instruction
    
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
        await message.answer(" Мир зашумел... Подожди мгновение и попробуй снова.")
        print(f"DeepSeek Error: {e}")

async def check_and_greet_if_needed(message: types.Message):
    user_id = message.from_user.id
    last_interaction = await get_last_interaction(user_id)
    
    if last_interaction is None:
        return True
    
    last_time = datetime.fromisoformat(last_interaction.replace('Z', '+00:00').replace('+00:00', ''))
    now = datetime.now()
    
    hours_diff = (now - last_time).total_seconds() / 3600
    is_new_day = now.date() != last_time.date()
    
    return hours_diff > 12 or is_new_day

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
        await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="Markdown")

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
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    theme = get_time_theme()
    user_lang = await get_user_lang(message.from_user.id)
    await message.answer(
        f"{theme['emoji']} **Выбери практику:**",
        reply_markup=get_main_menu_keyboard(user_lang),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("session_"))
async def process_session(callback: CallbackQuery):
    session_type = callback.data.replace("session_", "")
    user_lang = await get_user_lang(callback.from_user.id)
    
    sessions_ru = {
        "stop_world": "🌑 **Остановить мир**\n\nПрактика прерывания автоматизмов мышления.\nОпиши ситуацию, которая заела.",
        "death": "💀 **Разговор со смертью**\n\nСмерть стоит за твоим левым плечом...\nЧто бы ты сделал иначе, если бы знал, что это последний день?",
        "heart": "❤️ **Путь с сердцем**\n\nЕсть ли радость в том, что ты делаешь?\nИли лишь долг и страх?",
        "dreams": " **Видение снов**\n\nРасскажи свой сон. Мы посмотрим на него через призму второго внимания.",
        "intention": "⚡ **Намерение**\n\nСформулируй своё намерение. Не цель — а намерение. Почувствуй разницу."
    }
    
    sessions_en = {
        "stop_world": "🌑 **Stop the World**\n\nPractice of interrupting mental automatisms.\nDescribe the situation that's stuck.",
        "death": "💀 **Talk with Death**\n\nDeath stands at your left shoulder...\nWhat would you do differently if today was your last day?",
        "heart": "❤️ **Path with Heart**\n\nIs there joy in what you're doing?\nOr only duty and fear?",
        "dreams": " **Dreaming**\n\nTell me your dream. We'll look at it through the lens of second attention.",
        "intention": "⚡ **Intention**\n\nFormulate your intention. Not a goal — but intention. Feel the difference."
    }
    
    sessions = sessions_en if user_lang == "en" else sessions_ru
    text = sessions.get(session_type, "🤔 Choose a practice from the menu" if user_lang == "en" else " Выбери практику из меню")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(lambda message: message.voice)
async def handle_voice(message: types.Message):
    if not os.getenv("OPENAI_API_KEY"):
        await message.answer("🔇 Voice recognition unavailable. Please type.")
        return

    await message.answer("🎤 Listening...")
    
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
        print(f"Recognized text: {recognized_text}")
        
        await message.answer(f"📝 _Recognized: {recognized_text}_", parse_mode="Markdown")
        await process_text_message(message, recognized_text)
        
    except Exception as e:
        await message.answer("🌫 Voice dissolved in the wind. Couldn't recognize. Try again or type.")
        print(f"Whisper Error: {e}")

@dp.message()
async def handle_text(message: types.Message):
    if not message.text:
        return
    
    user_id = message.from_user.id
    needs_greeting = await check_and_greet_if_needed(message)
    
    if needs_greeting:
        theme = get_time_theme()
        user_lang = await get_user_lang(user_id)
        
        greeting_ru = (
            f"{theme['emoji']} **{theme['greeting']}**\n\n"
            f"{theme['description']}\n\n"
            f" Рад видеть тебя снова, воин.\n\n"
            f"{theme['color']} Как твоё настроение сегодня?"
        )
        
        greeting_en = (
            f"{theme['emoji']} **{theme['greeting']}**\n\n"
            f"{theme['description']}\n\n"
            f"🪶 Glad to see you again, warrior.\n\n"
            f"{theme['color']} How are you feeling today?"
        )
        
        greeting_text = greeting_en if user_lang == "en" else greeting_ru
        
        try:
            await message.answer_photo(
                photo=theme["photo_url"],
                caption=greeting_text,
                reply_markup=get_mood_keyboard(user_lang),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Photo error: {e}")
            await message.answer(greeting_text, reply_markup=get_mood_keyboard(user_lang), parse_mode="Markdown")
        
        await save_message(user_id, "user", message.text)
        return
    
    await process_text_message(message, message.text)

@dp.callback_query(lambda c: c.data == "mood_check")
async def mood_check(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = "😊 **How do you feel?**" if user_lang == "en" else "😊 **Как ты себя чувствуешь?**"
    await callback.message.answer(
        text,
        reply_markup=get_mood_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("mood_") and c.data != "mood_check")
async def mood_select(callback: CallbackQuery):
    mood = callback.data.replace("mood_", "")
    user_id = callback.from_user.id
    user_lang = await get_user_lang(user_id)
    
    await save_mood(user_id, mood)
    
    responses_ru = {
        "good": "😊 Рад, что у тебя всё хорошо! Воин сохраняет ясность в радости.",
        "ok": "😐 Нормально — это тоже путь. Воин не судит своё состояние.",
        "bad": "😔 Я слышу тебя. Иногда признать боль — первый шаг к исцелению. Расскажи, что случилось?",
        "anxiety": "😰 Тревога — это ветер, который пытается сбить тебя с пути. Но воин стоит твёрдо. Давай подышим вместе?"
    }
    
    responses_en = {
        "good": "😊 Glad you're doing well! A warrior maintains clarity in joy.",
        "ok": "😐 Okay is also a path. A warrior doesn't judge their state.",
        "bad": "😔 I hear you. Sometimes acknowledging pain is the first step to healing. Tell me what happened?",
        "anxiety": "😰 Anxiety is wind trying to knock you off your path. But a warrior stands firm. Let's breathe together?"
    }
    
    responses = responses_en if user_lang == "en" else responses_ru
    text = responses.get(mood, "I understand you.")
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "breathing")
async def breathing_menu(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = "🧘 **Выбери дыхательную практику:**\n\n🌊 **4-7-8** — расслабление и сон\n🌬️ **Равное дыхание** — баланс и спокойствие\n🔥 **Огненное дыхание** — энергия и бодрость"
    text_en = "🧘 **Choose breathing technique:**\n\n🌊 **4-7-8** — relaxation & sleep\n🌬️ **Equal breathing** — balance & calm\n🔥 **Fire breathing** — energy & vitality"
    
    await callback.message.answer(
        text_en if user_lang == "en" else text_ru,
        reply_markup=get_breathing_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("breathe_"))
async def breathing_exercise(callback: CallbackQuery):
    exercise = callback.data.replace("breathe_", "")
    user_lang = await get_user_lang(callback.from_user.id)
    
    exercises_ru = {
        "478": "🌊 **Техника 4-7-8**\n\n1. Вдох через нос — **4 секунды**\n2. Задержи дыхание — **7 секунд**\n3. Выдох через рот — **8 секунд**\n\nПовтори 4 раза. Идеально перед сном. 💤",
        "equal": "🌬️ **Равное дыхание**\n\n1. Вдох — **4 секунды**\n2. Выдох — **4 секунды**\n\nПовтори 5-10 раз. Возвращает в настоящее мгновение. ⚖️",
        "fire": "🔥 **Огненное дыхание**\n\n1. Резкий выдох через нос\n2. Вдох происходит автоматически\n3. Темп: 1-2 цикла в секунду\n\nДелай 30 секунд. Даёт мощный прилив энергии! ⚡"
    }
    
    exercises_en = {
        "478": "🌊 **4-7-8 Technique**\n\n1. Inhale through nose — **4 seconds**\n2. Hold breath — **7 seconds**\n3. Exhale through mouth — **8 seconds**\n\nRepeat 4 times. Perfect before sleep. 💤",
        "equal": "️ **Equal Breathing**\n\n1. Inhale — **4 seconds**\n2. Exhale — **4 seconds**\n\nRepeat 5-10 times. Returns you to the present moment. ⚖️",
        "fire": "🔥 **Fire Breathing**\n\n1. Sharp exhale through nose\n2. Inhale happens automatically\n3. Pace: 1-2 cycles per second\n\nDo for 30 seconds. Gives powerful energy boost! ⚡"
    }
    
    exercises = exercises_en if user_lang == "en" else exercises_ru
    text = exercises.get(exercise, "Choose an exercise from the menu.")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "consultation")
async def consultation_menu(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = (
        "👤 **Личная консультация**\n\n"
        "🪶 Иногда нужен проводник, чтобы увидеть путь яснее.\n\n"
        "💬 **Текстовая консультация (30 мин) — 1500₽**\n"
        "• Переписка в Telegram\n"
        "• Глубокий разбор ситуации\n"
        "• Практики и рекомендации\n\n"
        "🎙️ **Голосовая консультация (60 мин) — 3000₽**\n"
        "• Созвон в Telegram/WhatsApp\n"
        "• Живой диалог\n"
        "• Мгновенная обратная связь\n\n"
        "Выбери формат:"
    )
    
    text_en = (
        "👤 **Personal Consultation**\n\n"
        " Sometimes you need a guide to see the path more clearly.\n\n"
        "💬 **Text consultation (30 min) — 1500₽**\n"
        "• Chat in Telegram\n"
        "• Deep analysis of your situation\n"
        "• Practices and recommendations\n\n"
        "🎙️ **Voice consultation (60 min) — 3000₽**\n"
        "• Call via Telegram/WhatsApp\n"
        "• Live dialogue\n"
        "• Instant feedback\n\n"
        "Choose format:"
    )
    
    text = text_en if user_lang == "en" else text_ru
    
    await callback.message.answer(
        text,
        reply_markup=get_consultation_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "consult_text")
async def book_text_consult(callback: CallbackQuery):
    await process_consultation_booking(callback, "text")

@dp.callback_query(lambda c: c.data == "consult_voice")
async def book_voice_consult(callback: CallbackQuery):
    await process_consultation_booking(callback, "voice")

async def process_consultation_booking(callback: CallbackQuery, consult_type: str):
    user_id = callback.from_user.id
    user_lang = await get_user_lang(user_id)
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    
    if consult_type == "text":
        type_name_ru = "Текстовая консультация (30 мин) — 1500₽"
        type_name_en = "Text consultation (30 min) — 1500₽"
    else:
        type_name_ru = "Голосовая консультация (60 мин) — 3000₽"
        type_name_en = "Voice consultation (60 min) — 3000₽"
    
    YOUR_ID = 862373702  # ← ЗАМЕНИ НА СВОЙ TELEGRAM ID!
    
    notification_ru = (
        f"🔔 **НОВАЯ ЗАЯВКА!**\n\n"
        f" Тип: {type_name_ru}\n"
        f"👤 Имя: {full_name}\n"
        f"🔗 Username: @{username if username else 'нет'}\n"
        f"🆔 ID: {user_id}\n\n"
        f"Напиши этому человеку, чтобы договориться о времени!"
    )
    
    notification_en = (
        f"🔔 **NEW REQUEST!**\n\n"
        f" Type: {type_name_en}\n"
        f"👤 Name: {full_name}\n"
        f"🔗 Username: @{username if username else 'none'}\n"
        f"🆔 ID: {user_id}\n\n"
        f"Contact this person to schedule!"
    )
    
    try:
        await bot.send_message(
            YOUR_ID,
            notification_en if user_lang == "en" else notification_ru,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Failed to send notification: {e}")
    
    text_ru = (
        f"✅ **Заявка отправлена!**\n\n"
        f"🪶 Ты выбрал: {type_name_ru}\n\n"
        f"Я свяжусь с тобой в течение 24 часов в Telegram.\n\n"
        f"Если нужно срочно — напиши мне напрямую: @Yuli_kor"
    )
    
    text_en = (
        f"✅ **Request sent!**\n\n"
        f" You chose: {type_name_en}\n\n"
        f"I'll contact you within 24 hours on Telegram.\n\n"
        f"If urgent — write me directly: @your_username"
    )
    
    text = text_en if user_lang == "en" else text_ru
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "consult_info")
async def consult_info(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = (
        "ℹ️ **Как это работает:**\n\n"
        "1️⃣ Выбираешь формат (текст или голос)\n"
        "2️⃣ Оставляешь заявку\n"
        "3️⃣ Я связываюсь с тобой в течение 24 часов\n"
        "4️⃣ Договариваемся об удобном времени\n"
        "5️ Проводим консультацию\n\n"
        "💳 **Оплата:**\n"
        "• Перевод на карту (Сбер, Тинькофф)\n"
        "• Оплата до начала сессии\n\n"
        " **С чем работаю:**\n"
        "• Тревога и страхи\n"
        "• Поиск пути и предназначения\n"
        "• Отношения\n"
        "• Внутренние конфликты\n"
        "• Духовный кризис\n\n"
        "Готов записаться? Выбери формат выше 👆"
    )
    
    text_en = (
        "ℹ️ **How it works:**\n\n"
        "1️⃣ Choose format (text or voice)\n"
        "2️ Leave a request\n"
        "3️⃣ I contact you within 24 hours\n"
        "4️⃣ We schedule convenient time\n"
        "5️⃣ Have the consultation\n\n"
        "💳 **Payment:**\n"
        "• Bank card transfer\n"
        "• Payment before session\n\n"
        "🎯 **I work with:**\n"
        "• Anxiety and fears\n"
        "• Finding path and purpose\n"
        "• Relationships\n"
        "• Inner conflicts\n"
        "• Spiritual crisis\n\n"
        "Ready to book? Choose format above 👆"
    )
    
    text = text_en if user_lang == "en" else text_ru
    
    await callback.message.answer(
        text,
        reply_markup=get_consultation_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    theme = get_time_theme()
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = f"{theme['emoji']} **Главное меню:**"
    text_en = f"{theme['emoji']} **Main Menu:**"
    
    await callback.message.answer(
        text_en if user_lang == "en" else text_ru,
        reply_markup=get_main_menu_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "premium_sessions")
async def process_premium(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = "🔒 **Premium-сессии**\n\n🦅 Видение снов\n⚡ Намерение\n️ Карта пути\n\nДоступно по подписке. Оформить?"
    text_en = "🔒 **Premium Sessions**\n\n Dreaming\n⚡ Intention\n️ Path Map\n\nAvailable with subscription. Sign up?"
    
    await callback.message.answer(
        text_en if user_lang == "en" else text_ru,
        reply_markup=get_premium_sessions_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "subscribe")
async def process_subscribe(callback: CallbackQuery):
    await handle_subscribe(callback)

async def main():
    await init_db()
    print("🪶 Бот запущен и готов к пути воина...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
