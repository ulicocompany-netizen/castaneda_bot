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

def get_time_theme():
    hour = datetime.datetime.now().hour
    
    if 6 <= hour < 12:
        return {
            "emoji": "☀️",
            "greeting": "Доброе утро, воин",
            "description": "Солнце встаёт из-за горизонта. Новый день — новые возможности.",
            "color": "🌅",
            "photo_url": "https://i.ibb.co/ymSC6nmb"  # ← ЗАМЕНИ НА СВОЮ ССЫЛКУ
        }
    elif 12 <= hour < 17:
        return {
            "emoji": "🌤️",
            "greeting": "Добрый день, путник",
            "description": "Солнце в зените. Время действия и силы.",
            "color": "☀️",
            "photo_url": "https://i.ibb.co/HD4ND8QS"  # ← ЗАМЕНИ НА СВОЮ ССЫЛКУ
        }
    elif 17 <= hour < 22:
        return {
            "emoji": "🌆",
            "greeting": "Добрый вечер, странник",
            "description": "Солнце садится. Время размышлений и видения.",
            "color": "🌄",
            "photo_url": "https://i.ibb.co/q3RTtMDG"  # ← ЗАМЕНИ НА СВОЮ ССЫЛКУ
        }
    else:
        return {
            "emoji": "🌙",
            "greeting": "Доброй ночи, видящий",
            "description": "Ночь наступила. Время снов и второго внимания.",
            "color": "✨",
            "photo_url": "https://i.ibb.co/7dS4jgCm"  # ← ЗАМЕНИ НА СВОЮ ССЫЛКУ
        }

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
    except:
        await message.answer(
            text,
            reply_markup=get_language_keyboard(),
            parse_mode="Markdown"
        )

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

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    theme = get_time_theme()
    await message.answer(
        f"{theme['emoji']} **Выбери практику:**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

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

@dp.message()
async def handle_chat(message: types.Message):
    user_id = message.from_user.id
    context = await get_context(user_id)
    
    messages = [{"role": "system", "content": CASTANEDA_THERAPY_PROMPT}]
    messages.extend(context)
    messages.append({"role": "user", "content": message.text})
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.75,
            max_tokens=600
        )
        reply = response.choices[0].message.content
        await save_message(user_id, "user", message.text)
        await save_message(user_id, "assistant", reply)
        await message.answer(reply)
    except Exception as e:
        await message.answer("🌫 Мир зашумел... Подожди мгновение и попробуй снова.")
        print(f"DeepSeek Error: {e}")

async def main():
    await init_db()
    print("🪶 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
