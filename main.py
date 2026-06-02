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

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

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
        await message.answer("🌫 Мир зашумел... Подожди мгновение и попробуй снова.")
        print(f"DeepSeek Error: {e}")

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
        "dreams": "🦅 **Видение снов**\n\nРасскажи свой сон. Мы посмотрим на него через призму второго внимания.",
        "intention": "⚡ **Намерение**\n\nСформулируй своё намерение. Не цель — а намерение. Почувствуй разницу."
    }
    
    sessions_en = {
        "stop_world": "🌑 **Stop the World**\n\nPractice of interrupting mental automatisms.\nDescribe the situation that's stuck.",
        "death": "💀 **Talk with Death**\n\nDeath stands at your left shoulder...\nWhat would you do differently if today was your last day?",
        "heart": "❤️ **Path with Heart**\n\nIs there joy in what you're doing?\nOr only duty and fear?",
        "dreams": "🦅 **Dreaming**\n\nTell me your dream. We'll look at it through the lens of second attention.",
        "intention": "⚡ **Intention**\n\nFormulate your intention. Not a goal — but intention. Feel the difference."
    }
    
    sessions = sessions_en if user_lang == "en" else sessions_ru
    text = sessions.get(session_type, "🤔 Choose a practice from the menu" if user_lang == "en" else "🤔 Выбери практику из меню")
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
    if message.text:
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
        "equal": "🌬️ **Equal Breathing**\n\n1. Inhale — **4 seconds**\n2. Exhale — **4 seconds**\n\nRepeat 5-10 times. Returns you to the present moment. ⚖️",
        "fire": "🔥 **Fire Breathing**\n\n1. Sharp exhale through nose\n2. Inhale happens automatically\n3. Pace: 1-2 cycles per second\n\nDo for 30 seconds. Gives powerful energy boost! ⚡"
    }
    
    exercises = exercises_en if user_lang == "en" else exercises_ru
    text = exercises.get(exercise, "Choose an exercise from the menu.")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "emergency")
async def emergency(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = "🆘 **Ты не один, воин.**\n\n📞 **Телефон доверия (Россия):** 8-800-2000-122 (бесплатно)\n\nЕсли тебе сейчас очень плохо — позвони. Это не слабость, это мудрость.\n\n🧘 Или попробуй быструю технику самопомощи:"
    text_en = "🆘 **You're not alone, warrior.**\n\n📞 **Helpline (Russia):** 8-800-2000-122 (free)\n\nIf you feel really bad right now — call. It's not weakness, it's wisdom.\n\n🧘 Or try a quick self-help technique:"
    
    await callback.message.answer(
        text_en if user_lang == "en" else text_ru,
        reply_markup=get_emergency_keyboard(user_lang)
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "emergency_help")
async def emergency_help(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    
    text_ru = "🧘 **Быстрая техника заземления 5-4-3-2-1:**\n\n👀 Назови **5 вещей**, которые ты видишь\n👂 **4 звука**, которые слышишь\n✋ **3 ощущения** в теле\n👃 **2 запаха**\n👅 **1 вкус**\n\nЭто возвращает в настоящее. Ты здесь. Ты в безопасности. 🌿"
    text_en = "🧘 **Quick grounding technique 5-4-3-2-1:**\n\n👀 Name **5 things** you can see\n👂 **4 sounds** you can hear\n✋ **3 sensations** in your body\n👃 **2 smells**\n👅 **1 taste**\n\nThis returns you to the present. You are here. You are safe. 🌿"
    
    await callback.message.answer(
        text_en if user_lang == "en" else text_ru
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
    
    text_ru = "🔒 **Premium-сессии**\n\n🦅 Видение снов\n⚡ Намерение\n🗺️ Карта пути\n\nДоступно по подписке. Оформить?"
    text_en = "🔒 **Premium Sessions**\n\n🦅 Dreaming\n⚡ Intention\n🗺️ Path Map\n\nAvailable with subscription. Sign up?"
    
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
