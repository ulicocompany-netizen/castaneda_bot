import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Импорт наших модулей
from prompts import CASTANEDA_THERAPY_PROMPT
from database import init_db, get_user_lang, set_user_lang, save_message, get_context
from keyboards import get_language_keyboard, get_main_menu_keyboard, get_premium_sessions_keyboard
from payments import handle_subscribe

# Загрузка переменных из .env
load_dotenv()

# Инициализация бота и API
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🪶 Добро пожаловать на путь воина.\n\n"
        "Выбери язык общения, затем задай вопрос или поделись тем, что тяготит.\n"
        "Помни: мир — лишь описание. Готов ли ты его остановить?",
        reply_markup=get_language_keyboard()
    )

# Обработка выбора языка
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def process_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    await set_user_lang(user_id, lang)
    
    lang_names = {"ru": "🇷🇺 Русский", "en": "🇺 English", "es": "🇸 Español"}
    
    await callback.message.answer(
        f"✅ Язык установлен: {lang_names.get(lang, lang)}\n\n"
        "Теперь напиши что-нибудь, или используй /menu для выбора сессии.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

# Команда /menu
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer(
        "🌑 Выбери практику:",
        reply_markup=get_main_menu_keyboard()
    )

# Обработка кнопок меню
@dp.callback_query(lambda c: c.data.startswith("session_"))
async def process_session(callback: CallbackQuery):
    session_type = callback.data.replace("session_", "")
    
    sessions = {
        "stop_world": "🪶 **Остановить мир**\n\nПрактика прерывания автоматизмов мышления.\nОпиши ситуацию, которая заела.",
        "death": "🌑 **Разговор со смертью**\n\nСмерть стоит за твоим левым плечом...\nЧто бы ты сделал иначе, если бы знал, что это последний день?",
        "heart": "✨ **Путь с сердцем**\n\nЕсть ли радость в том, что ты делаешь?\nИли лишь долг и страх?",
        "dreams": "🦅 **Видение снов**\n\nРасскажи свой сон. Мы посмотрим на него через призму второго внимания.",
        "intention": "🔥 **Намерение**\n\nСформулируй своё намерение. Не цель — а намерение. Почувствуй разницу."
    }
    
    await callback.message.answer(
        sessions.get(session_type, "Выбери практику из меню"),
        reply_markup=get_premium_sessions_keyboard() if session_type in ["dreams", "intention"] else None
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "premium_sessions")
async def process_premium(callback: CallbackQuery):
    await callback.message.answer(
        "🔒 **Premium-сессии**\n\n"
        "🦅 Видение снов\n"
        "🔥 Намерение\n"
        "💫 Карта пути\n\n"
        "Доступно по подписке. Оформить?",
        reply_markup=get_premium_sessions_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "subscribe")
async def process_subscribe(callback: CallbackQuery):
    await handle_subscribe(callback)

# Обработка обычных сообщений
@dp.message()
async def handle_chat(message: types.Message):
    user_id = message.from_user.id
    
    # Получаем контекст из базы
    context = await get_context(user_id)
    
    # Формируем сообщения для API
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
        
        # Сохраняем в базу
        await save_message(user_id, "user", message.text)
        await save_message(user_id, "assistant", reply)
        
        await message.answer(reply)
        
    except Exception as e:
        await message.answer("🌫 Мир зашумел... Подожди мгновение и попробуй снова.")
        print(f"DeepSeek Error: {e}")

# Запуск
async def main():
    await init_db()
    print("🪶 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
