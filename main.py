import os
import asyncio
import datetime
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
    delete_user_data,
    set_tale_step, get_tale_step, set_tale1_seen, is_tale1_seen,
    log_fable_event
)
from keyboards import (
    get_language_keyboard, get_main_menu_keyboard, get_mood_keyboard,
    get_breathing_keyboard, get_consultation_keyboard,
    get_documents_keyboard, get_age_keyboard,
    get_subscription_keyboard, get_payment_keyboard,
    get_fable_p1_keyboard, get_fable_p2_keyboard, get_fable_p3_keyboard,
    get_fable_do_keyboard, get_fable_end_keyboard, get_fable_soon_keyboard,
    get_fable_done_marker
)
from documents import (
    POLICY_RU, TERMS_RU, OFFER_RU,
    POLICY_EN, TERMS_EN, OFFER_EN
)
from reminders import get_random_reminder, should_send_reminder
from fables import (
    COVER_CAPTION_RU, COVER_CAPTION_EN,
    P1_RU, P1_EN, P2_RU, P2_EN, P3_RU, P3_EN,
    DO_RU, DO_EN, END_RU, END_EN, SOON_RU, SOON_EN
)

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
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

# Твой file_id обложки уже вставлен в код ниже
COVER_FILE_ID = "https://raw.githubusercontent.com/Yuli_kor/castaneda_bot/main/images/fable_cover.png"

def get_time_theme(lang="ru"):
    utc_now = datetime.now(timezone.utc)
    moscow_tz = timezone(timedelta(hours=3))
    moscow_time = utc_now.astimezone(moscow_tz)
    hour = moscow_time.hour
    
    if lang == "en":
        if 6 <= hour < 12:
            return {"emoji": "☀️", "greeting": "Good morning, warrior", "description": "The sun rises over the horizon. A new day — new opportunities.", "color": "🌅", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/утро.jpeg"}
        elif 12 <= hour < 17:
            return {"emoji": "🌤️", "greeting": "Good afternoon, traveler", "description": "The sun is at its zenith. Time of action and power.", "color": "☀️", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/день1.jpeg"}
        elif 17 <= hour < 22:
            return {"emoji": "🌆", "greeting": "Good evening, wanderer", "description": "The sun sets. Time of reflection and vision.", "color": "🌄", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/сумерки.jpeg"}
        else:
            return {"emoji": "🌙", "greeting": "Good night, seer", "description": "Night has come. Time of dreams and second attention.", "color": "✨", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/ночь.jpeg"}
    else:
        if 6 <= hour < 12:
            return {"emoji": "☀️", "greeting": "Доброе утро, воин", "description": "Солнце встаёт из-за горизонта. Новый день — новые возможности.", "color": "🌅", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/утро.jpeg"}
        elif 12 <= hour < 17:
            return {"emoji": "🌤️", "greeting": "Добрый день, путник", "description": "Солнце в зените. Время действия и силы.", "color": "☀️", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/день1.jpeg"}
        elif 17 <= hour < 22:
            return {"emoji": "🌆", "greeting": "Добрый вечер, странник", "description": "Солнце садится. Время размышлений и видения.", "color": "🌄", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/сумерки.jpeg"}
        else:
            return {"emoji": "🌙", "greeting": "Доброй ночи, видящий", "description": "Ночь наступила. Время снов и второго внимания.", "color": "✨", "photo_url": "https://raw.githubusercontent.com/ulicocompany-netizen/castaneda_bot/main/images/ночь.jpeg"}

async def process_text_message(message: types.Message, text: str):
    user_id = message.from_user.id
    context = await get_context(user_id)
    user_lang = await get_user_lang(user_id)
    
    if user_lang == "ru":
        lang_instruction = "\n\n🔴 ВАЖНОЕ ПРАВИЛО:\n- Пользователь пишет на РУССКОМ языке\n- Ты ДОЛЖЕН отвечать ТОЛЬКО на РУССКОМ\n- НИКАКОГО английского в ответах"
    else:
        lang_instruction = "\n\n IMPORTANT RULE:\n- User writes in ENGLISH\n- You MUST respond ONLY in ENGLISH\n- NO Russian in your answers"
    
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
            max_tokens=1000
        )
        reply = response.choices[0].message.content
        await save_message(user_id, "user", text)
        await save_message(user_id, "assistant", reply)
        await message.answer(reply)
    except Exception as e:
        await message.answer("Мир зашумел... Подожди мгновение и попробуй снова.")
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
    if user_id == YOUR_ID:
        return True
    if await is_subscribed(user_id):
        return True
    messages_count = await get_messages_today(user_id)
    return messages_count < FREE_MESSAGES_LIMIT

async def send_limit_message(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    text_ru = "⚠️ **Ты достиг дневного лимита**\n\nБесплатно доступно 5 сообщений в день.\n\n🌟 **Оформи подписку** → /subscribe"
    text_en = "⚠️ **You've reached the daily limit**\n\nFree version allows 5 messages per day.\n\n🌟 **Subscribe** → /subscribe"
    text = text_en if user_lang == "en" else text_ru
    await message.answer(text, parse_mode="Markdown")

# ============================================
# 1. ВСЕ КОМАНДЫ
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    context = await get_context(user_id)
    age_confirmed = any(msg["content"] == "age_confirmed" for msg in context if msg["role"] == "system")
    
    if age_confirmed:
        user_lang = await get_user_lang(user_id)
        theme = get_time_theme(user_lang)
        text_ru = f"{theme['emoji']} **{theme['greeting']}**\n\n{theme['description']}\n\n🪶 Рад видеть тебя снова, воин."
        text_en = f"{theme['emoji']} **{theme['greeting']}**\n\n{theme['description']}\n\n🪶 Glad to see you again, warrior."
        text = text_en if user_lang == "en" else text_ru
        
        try:
            await message.answer_photo(photo=theme["photo_url"], caption=text, reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")
        except:
            await message.answer(text, reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")
    else:
        user_lang = await get_user_lang(user_id)
        theme = get_time_theme(user_lang)
        text_ru = f"🦅 **ПЕРЕСТУПИТЬ ПОРОГ**\n\n{theme['emoji']} *{theme['greeting']}*\n\nПуть воина — не для детей.\nОн требует зрелости, смелости и готовности встретиться с собой настоящим.\n\n⚠️ Этот путь — для тех, кому есть 18.\n\n**Выберите язык / Choose language:**"
        text_en = f"🦅 **CROSS THE THRESHOLD**\n\n{theme['emoji']} *{theme['greeting']}*\n\nThe warrior's path is not for children.\nIt requires maturity, courage, and readiness to meet your true self.\n\n⚠️ This path is for those who are 18+.\n\n**Выберите язык / Choose language:**"
        text = text_en if user_lang == "en" else text_ru
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(text="✅ Мне есть 18 / I am 18+", callback_data="age_yes")]
        ])
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    theme = get_time_theme(user_lang)
    text_ru = f"{theme['emoji']} **Выбери практику:**\n\n🌑 **Остановить мир**\n💀 **Разговор со смертью**\n❤️ **Путь с сердцем**\n🦅 **Видение снов**\n⚡ **Намерение**\n\n🧘 **Дыхание**\n😊 **Настроение**\n👤 **Консультация**"
    text_en = f"{theme['emoji']} **Choose your practice:**\n\n🌑 **Stop the World**\n💀 **Talk with Death**\n❤️ **Path with Heart**\n🦅 **Dreaming**\n⚡ **Intention**\n\n🧘 **Breathing**\n😊 **Mood**\n👤 **Consultation**"
    text = text_en if user_lang == "en" else text_ru
    await message.answer(text, reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")

@dp.message(Command("privacy"))
async def cmd_privacy(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    text = POLICY_EN if user_lang == "en" else POLICY_RU
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="Markdown")

@dp.message(Command("terms"))
async def cmd_terms(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    text = TERMS_EN if user_lang == "en" else TERMS_RU
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="Markdown")

@dp.message(Command("offer"))
async def cmd_offer(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    text = OFFER_EN if user_lang == "en" else OFFER_RU
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="Markdown")

@dp.message(Command("delete_data"))
async def cmd_delete_data(message: types.Message):
    user_id = message.from_user.id
    user_lang = await get_user_lang(user_id)
    await delete_user_data(user_id)
    text = "🗑 **Your trace is erased.**\n\nAll data deleted." if user_lang == "en" else "🗑 **Твой след стёрт.**\n\nВсе данные удалены. Путь начинается с чистого листа. 🪶"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if await is_subscribed(user_id):
        text = "✅ **Subscription active**\n\n🪶 The path is open." if user_lang == "en" else "✅ **Подписка активна**\n\n🪶 Путь открыт."
    else:
        text_ru = "🌟 **ПРЕМИУМ-ПОДПИСКА**\n\n🔓 Видение снов, Намерение, Безлимитные сообщения.\n\n💰 1 луна — 990₽ | 3 луны — 2490₽ | 6 лун — 3990₽\n\nВыбери свой путь:"
        text_en = "🌟 **PREMIUM SUBSCRIPTION**\n\n🔓 Dreaming, Intention, Unlimited messages.\n\n💰 1 moon — 990₽ | 3 moons — 2490₽ | 6 moons — 3990₽\n\nChoose your path:"
        text = text_en if user_lang == "en" else text_ru
    await message.answer(text, reply_markup=get_subscription_keyboard(user_lang), parse_mode="Markdown")

@dp.message(Command("my_subscription"))
async def cmd_my_subscription(message: types.Message):
    user_lang = await get_user_lang(message.from_user.id)
    user_id = message.from_user.id
    if await is_subscribed(user_id):
        text = "✅ **Subscription active**\n\n🪶 The path is open." if user_lang == "en" else "✅ **Подписка активна**\n\n🪶 Путь открыт."
    else:
        text = "❌ **Subscription inactive**\n\n→ /subscribe" if user_lang == "en" else "❌ **Подписка не активна**\n\n→ /subscribe"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("approve"))
async def cmd_approve(message: types.Message):
    if message.from_user.id != YOUR_ID: return
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("Использование: /approve <user_id> <days>")
            return
        user_id, days = int(parts[1]), int(parts[2])
        await set_subscription(user_id, days)
        await bot.send_message(user_id, f"🎉 **Подписка активирована!**\n\n🪶 Путь открыт на {days} дней.", parse_mode="Markdown")
        await message.answer(f"✅ Подписка активирована для {user_id} на {days} дней")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ============================================
# 2. ХЕНДЛЕРЫ СКАЗКИ (ВОРОНКА ПОКРОВОВ)
# ============================================

async def send_fable_p1(message, user_id: int, user_lang: str):
    text = P1_EN if user_lang == "en" else P1_RU
    await message.answer(text, reply_markup=get_fable_p1_keyboard(user_lang), parse_mode="HTML")
    await log_fable_event(user_id, "read1")

@dp.callback_query(lambda c: c.data == "tale_start")
async def tale_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_lang = await get_user_lang(user_id)
    await log_fable_event(user_id, "tale1_start")
    await set_tale_step(user_id, 0)
    
    caption = COVER_CAPTION_EN if user_lang == "en" else COVER_CAPTION_RU
    try:
        await callback.message.answer_photo(
            photo=COVER_FILE_ID,
            caption=caption,
            parse_mode="HTML"
        )
        await asyncio.sleep(1)
        await send_fable_p1(callback.message, user_id, user_lang)
    except Exception as e:
        print(f"❌ ОШИБКА ОТПРАВКИ ФОТО (tale_start): {e}")
        await callback.message.answer(f"⚠️ Ошибка загрузки обложки: {e}\n\nПопробуй получить file_id заново.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "start_journey")
async def start_journey(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_lang = await get_user_lang(user_id)
    tale1_seen = await is_tale1_seen(user_id)
    
    if not tale1_seen:
        await set_tale1_seen(user_id)
        await log_fable_event(user_id, "tale1_start")
        await set_tale_step(user_id, 0)
        
        caption = COVER_CAPTION_EN if user_lang == "en" else COVER_CAPTION_RU
        try:
            await callback.message.answer_photo(
                photo=COVER_FILE_ID,
                caption=caption,
                parse_mode="HTML"
            )
            await asyncio.sleep(1)
            await send_fable_p1(callback.message, user_id, user_lang)
        except Exception as e:
            print(f"❌ ОШИБКА ОТПРАВКИ ФОТО (start_journey): {e}")
            await callback.message.answer(f"⚠️ Ошибка загрузки обложки: {e}")
    else:
        theme = get_time_theme(user_lang)
        text_ru = f"{theme['emoji']} **Ты переступил порог.**\n\n{theme['description']}\n\n🦅 Добро пожаловать на путь воина.\n\nПрежде чем начать, ознакомься со Свитками Пути ниже 👇\n\n{theme['color']} Мир — лишь описание. Готов ли ты его остановить?"
        text_en = f"{theme['emoji']} **You have crossed the threshold.**\n\n{theme['description']}\n\n🪶 Welcome to the warrior's path.\n\nBefore you begin, review the Scrolls of the Path below 👇\n\n{theme['color']} The world is just a description. Ready to stop it?"
        text = text_en if user_lang == "en" else text_ru
        try:
            await callback.message.answer_photo(photo=theme["photo_url"], caption=text, reply_markup=get_documents_keyboard(user_lang), parse_mode="Markdown")
        except:
            await callback.message.answer(text, reply_markup=get_documents_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "t1_p2")
async def fable_t1_p2(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if await get_tale_step(user_id) >= 2: return await callback.answer()
    try: await callback.message.edit_reply_markup(reply_markup=get_fable_done_marker(user_lang))
    except: pass
    await set_tale_step(user_id, 2)
    await log_fable_event(user_id, "read2")
    await callback.message.answer(P2_EN if user_lang == "en" else P2_RU, reply_markup=get_fable_p2_keyboard(user_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "t1_p3")
async def fable_t1_p3(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if await get_tale_step(user_id) >= 3: return await callback.answer()
    try: await callback.message.edit_reply_markup(reply_markup=get_fable_done_marker(user_lang))
    except: pass
    await set_tale_step(user_id, 3)
    await log_fable_event(user_id, "read3")
    await callback.message.answer(P3_EN if user_lang == "en" else P3_RU, reply_markup=get_fable_p3_keyboard(user_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "t1_practice")
async def fable_t1_practice(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if await get_tale_step(user_id) >= 4: return await callback.answer()
    try: await callback.message.edit_reply_markup(reply_markup=get_fable_done_marker(user_lang))
    except: pass
    await set_tale_step(user_id, 4)
    await log_fable_event(user_id, "practice")
    await callback.message.answer(DO_EN if user_lang == "en" else DO_RU, reply_markup=get_fable_do_keyboard(user_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "t1_done")
async def fable_t1_done(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if await get_tale_step(user_id) >= 5: return await callback.answer()
    try: await callback.message.edit_reply_markup(reply_markup=get_fable_done_marker(user_lang))
    except: pass
    await set_tale_step(user_id, 5)
    await log_fable_event(user_id, "done")
    await callback.message.answer(END_EN if user_lang == "en" else END_RU, reply_markup=get_fable_end_keyboard(user_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "t1_next")
async def fable_t1_next(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if await get_tale_step(user_id) >= 6: return await callback.answer()
    try: await callback.message.edit_reply_markup(reply_markup=get_fable_done_marker(user_lang))
    except: pass
    await set_tale_step(user_id, 6)
    await log_fable_event(user_id, "want2")
    await callback.message.answer(SOON_EN if user_lang == "en" else SOON_RU, reply_markup=get_fable_soon_keyboard(user_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()

# ============================================
# 3. ОСТАЛЬНЫЕ CALLBACKS
# ============================================

@dp.callback_query(lambda c: c.data == "age_yes")
async def age_confirmed(callback: CallbackQuery):
    user_id = callback.from_user.id
    await save_message(user_id, "system", "age_confirmed")
    try:
        await callback.message.answer_video(
            video="BAACAgIAAxkBAAEsuxVqYg00AYskB59uAAHPgYnKu32nRzEAAm6nAAITkhhLYFzDv0GZ37w9BA",
            caption="🪶 Твой путь начинается здесь...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🦅 Я готов начать путь", callback_data="start_journey")]]),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ ОШИБКА ОТПРАВКИ ВИДЕО: {e}")
        await callback.message.answer(
            "🪶 Твой путь начинается здесь... (видео не загрузилось, но ты можешь продолжить)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🦅 Я готов начать путь", callback_data="start_journey")]])
        )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def process_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    await set_user_lang(user_id, lang)
    theme = get_time_theme(lang)
    lang_names = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
    text = f"✅ Language set: {lang_names.get(lang, lang)}\n\n{theme['emoji']} Now, please confirm your age by clicking the button below 👇" if lang == "en" else f"✅ Язык установлен: {lang_names.get(lang, lang)}\n\n{theme['emoji']} Теперь, пожалуйста, подтверди свой возраст, нажав кнопку ниже 👇"
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Мне есть 18 / I am 18+", callback_data="age_yes")]]), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("session_"))
async def process_session(callback: CallbackQuery):
    session_type = callback.data.replace("session_", "")
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if session_type in ["dreams", "intention"] and not await is_subscribed(user_id):
        text = "🔒 **This practice requires subscription**\n\n🌟 Subscribe to unlock them.\n\n→ /subscribe" if user_lang == "en" else "🔒 **Эта практика доступна по подписке**\n\n🌟 Оформи подписку, чтобы открыть их.\n\n→ /subscribe"
        await callback.message.answer(text, parse_mode="Markdown")
        return await callback.answer()
    
    sessions_ru = {"stop_world": "🌑 **Остановить мир**\n\nОпиши ситуацию, которая заела.", "death": "💀 **Разговор со смертью**\n\nЧто бы ты сделал иначе, если бы знал, что это последний день?", "heart": "❤️ **Путь с сердцем**\n\nЕсть ли радость в том, что ты делаешь?", "dreams": "🦅 **Видение снов**\n\nРасскажи свой сон.", "intention": "⚡ **Намерение**\n\nСформулируй своё намерение."}
    sessions_en = {"stop_world": "🌑 **Stop the World**\n\nDescribe the situation that's stuck.", "death": "💀 **Talk with Death**\n\nWhat would you do differently if today was your last day?", "heart": "❤️ **Path with Heart**\n\nIs there joy in what you're doing?", "dreams": "🦅 **Dreaming**\n\nTell me your dream.", "intention": "⚡ **Intention**\n\nFormulate your intention."}
    sessions = sessions_en if user_lang == "en" else sessions_ru
    await callback.message.answer(sessions.get(session_type, "🤔 Выбери практику из меню"), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "mood_check")
async def mood_check(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = "😊 **How do you feel?**" if user_lang == "en" else "😊 **Как ты себя чувствуешь?**"
    await callback.message.answer(text, reply_markup=get_mood_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("mood_") and c.data != "mood_check")
async def mood_select(callback: CallbackQuery):
    mood = callback.data.replace("mood_", "")
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    await save_mood(user_id, mood)
    responses_ru = {"good": "😊 Рад, что у тебя всё хорошо!", "ok": "😐 Нормально — это тоже путь.", "bad": "😔 Я слышу тебя. Расскажи, что случилось?", "anxiety": "😰 Тревога — это ветер. Давай подышим вместе?"}
    responses_en = {"good": "😊 Glad you're doing well!", "ok": "😐 Okay is also a path.", "bad": "😔 I hear you. Tell me what happened?", "anxiety": "😰 Anxiety is wind. Let's breathe together?"}
    responses = responses_en if user_lang == "en" else responses_ru
    await callback.message.answer(responses.get(mood, "I understand you."))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "breathing")
async def breathing_menu(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = "🧘 **Choose breathing technique:**\n\n🌊 **4-7-8**\n🌬️ **Equal breathing**\n🔥 **Fire breathing**" if user_lang == "en" else "🧘 **Выбери дыхательную практику:**\n\n🌊 **4-7-8**\n🌬️ **Равное дыхание**\n🔥 **Огненное дыхание**"
    await callback.message.answer(text, reply_markup=get_breathing_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("breathe_"))
async def breathing_exercise(callback: CallbackQuery):
    exercise = callback.data.replace("breathe_", "")
    user_lang = await get_user_lang(callback.from_user.id)
    exercises_ru = {"478": "**Техника 4-7-8**\n\n1. Вдох — 4 сек\n2. Задержка — 7 сек\n3. Выдох — 8 сек\n\nПовтори 4 раза. 💤", "equal": "🌬️ **Равное дыхание**\n\n1. Вдох — 4 сек\n2. Выдох — 4 сек\n\nПовтори 5-10 раз. ⚖️", "fire": "🔥 **Огненное дыхание**\n\nРезкий выдох через нос, вдох автоматически. Темп: 1-2 цикла в сек. Делай 30 сек. ⚡"}
    exercises_en = {"478": "**4-7-8 Technique**\n\n1. Inhale — 4s\n2. Hold — 7s\n3. Exhale — 8s\n\nRepeat 4 times. 💤", "equal": "🌬️ **Equal Breathing**\n\n1. Inhale — 4s\n2. Exhale — 4s\n\nRepeat 5-10 times. ⚖️", "fire": "🔥 **Fire Breathing**\n\nSharp exhale through nose, inhale automatically. Pace: 1-2 cycles/sec. Do for 30s. ⚡"}
    exercises = exercises_en if user_lang == "en" else exercises_ru
    await callback.message.answer(exercises.get(exercise, "Choose an exercise."), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "consultation")
async def consultation_menu(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text_ru = "👤 **Личная консультация**\n\n💬 **Текстовая (30 мин) — 1500₽**\n🎙️ **Голосовая (60 мин) — 3000₽**\n\nВыбери формат:"
    text_en = "👤 **Personal Consultation**\n\n💬 **Text (30 min) — 1500₽**\n🎙️ **Voice (60 min) — 3000₽**\n\nChoose format:"
    await callback.message.answer(text_en if user_lang == "en" else text_ru, reply_markup=get_consultation_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["consult_text", "consult_voice"])
async def book_consult(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    ctype = "text" if callback.data == "consult_text" else "voice"
    type_name = "Текстовая консультация (30 мин) — 1500₽" if ctype == "text" else "Голосовая консультация (60 мин) — 3000₽"
    type_name_en = "Text consultation (30 min) — 1500₽" if ctype == "text" else "Voice consultation (60 min) — 3000₽"
    
    notif = f"🔔 **НОВАЯ ЗАЯВКА!**\n\n📋 Тип: {type_name if user_lang=='ru' else type_name_en}\n👤 Имя: {callback.from_user.full_name}\n🔗 @{callback.from_user.username or 'нет'}\n🆔 ID: {user_id}"
    try: await bot.send_message(YOUR_ID, notif, parse_mode="Markdown")
    except: pass
    
    ans = f"✅ **Заявка отправлена!**\n\n🪶 Ты выбрал: {type_name if user_lang=='ru' else type_name_en}\n\nЯ свяжусь с тобой в течение 24 часов."
    await callback.message.answer(ans, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "consult_info")
async def consult_info(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = "ℹ️ **How it works:**\n\n1️⃣ Choose format\n2️⃣ Leave a request\n3️⃣ I contact you within 24h\n4️⃣ Payment before session" if user_lang == "en" else "ℹ️ **Как это работает:**\n\n1️⃣ Выбираешь формат\n2️⃣ Оставляешь заявку\n3️⃣ Я связываюсь в течение 24 часов\n4️⃣ Оплата до начала сессии"
    await callback.message.answer(text, reply_markup=get_consultation_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "documents_menu")
async def documents_menu(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    await callback.message.answer("📜 **Свитки Пути:**" if user_lang == "ru" else "📜 **Path Scrolls:**", reply_markup=get_documents_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "doc_privacy")
async def show_privacy(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = POLICY_EN if user_lang == "en" else POLICY_RU
    for i in range(0, len(text), 4000):
        try: await callback.message.answer(text[i:i+4000], parse_mode="Markdown")
        except: await callback.message.answer(text[i:i+4000])
    await callback.answer()

@dp.callback_query(lambda c: c.data == "doc_terms")
async def show_terms(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = TERMS_EN if user_lang == "en" else TERMS_RU
    for i in range(0, len(text), 4000):
        try: await callback.message.answer(text[i:i+4000], parse_mode="Markdown")
        except: await callback.message.answer(text[i:i+4000])
    await callback.answer()

@dp.callback_query(lambda c: c.data == "doc_offer")
async def show_offer(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    text = OFFER_EN if user_lang == "en" else OFFER_RU
    for i in range(0, len(text), 4000):
        try: await callback.message.answer(text[i:i+4000], parse_mode="Markdown")
        except: await callback.message.answer(text[i:i+4000])
    await callback.answer()

@dp.callback_query(lambda c: c.data == "subscribe_menu")
async def subscribe_menu(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    if await is_subscribed(user_id):
        text = "✅ **Subscription active**\n\n🪶 The path is open." if user_lang == "en" else "✅ **Подписка активна**\n\n🪶 Путь открыт."
    else:
        text_ru = "🌟 **ПРЕМИУМ-ПОДПИСКА**\n\n🔓 Видение снов, Намерение, Безлимитные сообщения.\n\n💰 1 луна — 990₽ | 3 луны — 2490₽ | 6 лун — 3990₽"
        text_en = "🌟 **PREMIUM SUBSCRIPTION**\n\n🔓 Dreaming, Intention, Unlimited messages.\n\n💰 1 moon — 990₽ | 3 moons — 2490₽ | 6 moons — 3990₽"
        text = text_en if user_lang == "en" else text_ru
    await callback.message.answer(text, reply_markup=get_subscription_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["sub_1", "sub_3", "sub_6"])
async def subscribe_choose(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    plan = callback.data.replace("sub_", "")
    plans = {"1": {"days": 30, "price": 990, "name_ru": "1 луна", "name_en": "1 moon"}, "3": {"days": 90, "price": 2490, "name_ru": "3 луны", "name_en": "3 moons"}, "6": {"days": 180, "price": 3990, "name_ru": "6 лун", "name_en": "6 moons"}}
    p = plans[plan]
    text_ru = f"📜 **Договор с Орлом**\n\nТы выбрал: **{p['name_ru']}** ({p['days']} дней)\n💰 Сумма: **{p['price']}₽**\n\n💳 Тинькофф: 5534 2000 5167 0180\n👤 Корытцына Ю.А.\n\nПосле оплаты нажми кнопку ниже."
    text_en = f"📜 **Pact with the Eagle**\n\nYou chose: **{p['name_en']}** ({p['days']} days)\n💰 Amount: **{p['price']}₽**\n\n💳 Tinkoff: 5534 2000 5167 0180\n👤 Koritsyna Y.A.\n\nAfter payment, click the button below."
    text = text_en if user_lang == "en" else text_ru
    await save_message(user_id, "system", f"subscription_plan_{plan}")
    await callback.message.answer(text, reply_markup=get_payment_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "payment_done")
async def payment_done(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    context = await get_context(user_id)
    plan = next((msg["content"].replace("subscription_plan_", "") for msg in reversed(context) if msg["role"] == "system" and msg["content"].startswith("subscription_plan_")), None)
    
    if not plan:
        text = "❌ Could not determine plan. Write /subscribe." if user_lang == "en" else "❌ Не удалось определить тариф. Напиши /subscribe."
    else:
        days = {"1": 30, "3": 90, "6": 180}.get(plan, 30)
        try: await bot.send_message(YOUR_ID, f"💳 **НОВАЯ ОПЛАТА!**\n\n👤 ID: {user_id}\n📋 Тариф: {days} дней\n\nАктивируй: `/approve {user_id} {days}`", parse_mode="Markdown")
        except: pass
        text = "✅ **Payment request accepted!**\n\n🪶 I'll check within 24h." if user_lang == "en" else "✅ **Заявка на оплату принята!**\n\n🪶 Я проверю оплату в течение 24 часов."
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_subscription")
async def my_subscription(callback: CallbackQuery):
    user_id, user_lang = callback.from_user.id, await get_user_lang(callback.from_user.id)
    text = "✅ **Subscription active**\n\n🪶 The path is open." if (await is_subscribed(user_id)) else ("❌ **Subscription inactive**\n\n→ /subscribe" if user_lang == "en" else "❌ **Подписка не активна**\n\n→ /subscribe")
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["main_menu", "menu"])
async def back_to_menu(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    theme = get_time_theme(user_lang)
    text = f"{theme['emoji']} **Main Menu:**" if user_lang == "en" else f"{theme['emoji']} **Главное меню:**"
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")
    await callback.answer()

# ============================================
# 4. ОБЩИЙ ОБРАБОТЧИК ТЕКСТА
# ============================================

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id
    context = await get_context(user_id)
    if not any(msg["content"] == "age_confirmed" for msg in context if msg["role"] == "system"):
        return await message.answer("🦅 Сначала подтверди, что тебе есть 18 лет.", reply_markup=get_age_keyboard(await get_user_lang(user_id)))
    if not await check_message_limit(user_id):
        return await send_limit_message(message)
    
    await bot.send_chat_action(message.chat.id, "typing")
    await message.answer("🎤 Слушаю тебя, воин... (распознаю голос)")
    try:
        file_info = await bot.get_file(message.voice.file_id)
        file_name = f"voice_{message.message_id}.ogg"
        await bot.download_file(file_info.file_path, file_name)
        with open(file_name, "rb") as audio_file:
            transcript = await openai_client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="ru" if await get_user_lang(user_id) == "ru" else "en")
        os.remove(file_name)
        await process_text_message(message, transcript.text)
    except Exception as e:
        print(f"Ошибка распознавания: {e}")
        await message.answer("🎤 Мир зашумел... Попробуй написать текстом.")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: types.Message):
    if not message.text: return
    user_id = message.from_user.id
    context = await get_context(user_id)
    
    if not any(msg["content"] == "age_confirmed" for msg in context if msg["role"] == "system"):
        user_lang = await get_user_lang(user_id)
        theme = get_time_theme(user_lang)
        text = f"🦅 **CROSS THE THRESHOLD**\n\n⚠️ This path is for those who are 18+.\n\n**Are you ready?**" if user_lang == "en" else f"🦅 **ПЕРЕСТУПИТЬ ПОРОГ**\n\n⚠️ Этот путь — для тех, кому есть 18.\n\n**Готов ли ты?**"
        return await message.answer(text, reply_markup=get_age_keyboard(user_lang), parse_mode="Markdown")
    
    if not await check_message_limit(user_id):
        return await send_limit_message(message)
    
    user_lang = await get_user_lang(user_id)
    text_lower = message.text.lower()
    keywords = ["видение снов", "расшифруй сон", "мой сон", "толкование сна", "сон приснился", "намерение", "работа с намерением"] if user_lang == "ru" else ["dream", "dreaming", "interpret my dream", "my dream", "intention"]
    
    if any(kw in text_lower for kw in keywords) and not await is_subscribed(user_id):
        text = "🔒 **This practice requires subscription**\n\n🌟 Subscribe to unlock them.\n\n→ /subscribe" if user_lang == "en" else "🔒 **Эта практика доступна по подписке**\n\n🌟 Оформи подписку, чтобы открыть их.\n\n→ /subscribe"
        return await message.answer(text, parse_mode="Markdown")
    
    await increment_messages_today(user_id)
    
    if await check_and_greet_if_needed(message):
        theme = get_time_theme(user_lang)
        greeting = f"{theme['emoji']} **{theme['greeting']}**\n\n{theme['description']}\n\n🪶 Glad to see you again, warrior.\n\n{theme['color']} How are you feeling today?" if user_lang == "en" else f"{theme['emoji']} **{theme['greeting']}**\n\n{theme['description']}\n\n🪶 Рад видеть тебя снова, воин.\n\n{theme['color']} Как твоё настроение сегодня?"
        try:
            await message.answer_photo(photo=theme["photo_url"], caption=greeting, reply_markup=get_mood_keyboard(user_lang), parse_mode="Markdown")
        except:
            await message.answer(greeting, reply_markup=get_mood_keyboard(user_lang), parse_mode="Markdown")
        await save_message(user_id, "user", message.text)
        return
    
    await process_text_message(message, message.text)

# ============================================
# 5. ФОНОВЫЕ ЗАДАЧИ И ЗАПУСК
# ============================================

async def daily_reminder_loop():
    await asyncio.sleep(60)
    while True:
        try:
            now = datetime.now()
            if now.hour == 12 and now.minute < 5:
                print("Starting daily reminder job...")
                users = await get_users_without_subscription()
                sent_count = 0
                for user_id, _ in users:
                    await asyncio.sleep(1)
                    try:
                        user_lang = await get_user_lang(user_id)
                        last_reminder = await get_last_reminder(user_id)
                        if not should_send_reminder(last_reminder, days_interval=5): continue
                        await bot.send_message(user_id, get_random_reminder(user_lang), parse_mode="Markdown")
                        await update_last_reminder(user_id)
                        sent_count += 1
                    except Exception as e:
                        print(f"Failed to remind {user_id}: {e}")
                print(f"✅ Daily reminders sent: {sent_count}")
            await asyncio.sleep(300)
        except Exception as e:
            print(f"Reminder loop error: {e}")
            await asyncio.sleep(60)

@dp.message(F.photo)
async def log_photo(message: types.Message):
    """Временный обработчик для получения file_id фото"""
    file_id = message.photo[-1].file_id
    print(f"\n{'='*60}")
    print(f"📸 ПОЛУЧЕНО ФОТО!")
    print(f"File ID: {file_id}")
    print(f"{'='*60}\n")
    await message.answer(f"✅ Фото получено!\n\nFile ID:\n`{file_id}`")

async def main():
    await init_db()
    print("🦅 Бот запущен и готов к пути воина...")
    asyncio.create_task(daily_reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())