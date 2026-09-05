# ============================================
# FEATURES.PY v5 — ДВУЯЗЫЧНЫЙ ИИ-ВОРОН
# ============================================
import os
import random
import asyncio
import traceback
import aiosqlite
from datetime import datetime

from aiogram import types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from openai import AsyncOpenAI

import texts_ru as RU
import texts_en as EN
from keyboards import get_main_menu_keyboard, get_breathing_keyboard
from database import get_user_lang
from voices import send_raven_voice, reset_voice_limit

DB_PATH = "bot.db"

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

RAVEN_SYSTEM = "Ты — Ворон, проводник по пути воина в стиле учения Карлоса Кастанеды. Говори хрипло, спокойно, без «успешного успеха». Используй образы дона Хуана: смерть как советчик, точка сборки, мотыльки внутреннего диалога, важность, безупречность, остановка мира, путь с сердцем. Отвечай КОРОТКО: 3-6 предложений, без списков и заголовков. LANGUAGE RULE: if the request starts with [LANG:EN] respond in English; if [LANG:RU] respond in Russian."

class StalkingStates(StatesGroup):
    waiting_answer = State()

class IndulgiStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()

# ---------- БД ----------
async def ensure_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS stalking_diary (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, task_text TEXT, user_response TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS indulgimeter_results (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, score INTEGER)")
        await db.commit()

async def save_stalking_entry(user_id, task_text, user_response):
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO stalking_diary (user_id, date, task_text, user_response) VALUES (?,?,?,?)", (user_id, datetime.now().isoformat(), task_text, user_response))
        await db.commit()

async def get_stalking_entries(user_id, limit=5):
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT date, task_text, user_response FROM stalking_diary WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
        return await cur.fetchall()

async def save_indulgi_score(user_id, score):
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO indulgimeter_results (user_id, date, score) VALUES (?,?,?)", (user_id, datetime.now().isoformat(), score))
        await db.commit()

# ---------- ПОМОЩНИКИ ----------
def lib(lang):
    return EN if lang == "en" else RU

def back_kb(lang="ru"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩ Menu" if lang == "en" else "↩ В меню", callback_data="main_menu")]])

def indulgi_kb(n, lang="ru"):
    rows = [[InlineKeyboardButton(text=o["text"], callback_data=o["callback"])] for o in lib(lang).INDULGI_QUESTIONS[n - 1]["options"]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def with_ps(text, user=None, lang="ru"):
    if random.random() < 0.3:
        L = lib(lang)
        name = getattr(user, "first_name", None)
        if name and random.random() < 0.5:
            text += "\n\n" + random.choice(L.PS_NAME_LINES).format(name=name)
        else:
            text += "\n\n" + random.choice(L.PS_LINES)
    return text

def err(e, where):
    print(f"❌ ОШИБКА ФИЧИ [{where}]: {e}")
    traceback.print_exc()

async def raven_ai(user_prompt, fallback, lang="ru"):
    try:
        tag = "[LANG:EN] " if lang == "en" else "[LANG:RU] "
        r = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": RAVEN_SYSTEM}, {"role": "user", "content": tag + user_prompt}],
            temperature=0.9,
            max_tokens=500
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        err(e, "raven_ai")
        return fallback

# ---------- РЕГИСТРАЦИЯ ----------
def register_features(dp, bot):
    last_task = {"stalking": {}, "shift": {}, "magic": {}}
    pending = {"task": {}, "response": {}}

    async def do_stalking(callback, state):
        user_id = callback.from_user.id
        lang = await get_user_lang(user_id)
        tasks = lib(lang).STALKING_TASKS
        task = random.choice(tasks)
        while task == last_task["stalking"].get(user_id) and len(tasks) > 1:
            task = random.choice(tasks)
        last_task["stalking"][user_id] = task
        pending["task"][user_id] = task
        await callback.message.answer(("🦅 The Raven watches.\n\n" if lang == "en" else "🦅 Ворон наблюдает.\n\n") + task)
        await state.set_state(StalkingStates.waiting_answer)

    async def do_shift(callback, state=None):
        user_id = callback.from_user.id
        lang = await get_user_lang(user_id)
        tasks = lib(lang).SHIFT_TASKS
        task = random.choice(tasks)
        while task == last_task["shift"].get(user_id) and len(tasks) > 1:
            task = random.choice(tasks)
        last_task["shift"][user_id] = task
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ I did it" if lang == "en" else "✅ Я сделал это", callback_data="shift_done")],
            [InlineKeyboardButton(text="↩ Menu" if lang == "en" else "↩ В меню", callback_data="main_menu")]
        ])
        await callback.message.answer(f"{task}\n\n" + ("When done — press the button below." if lang == "en" else "Когда выполнишь — нажми кнопку ниже."), reply_markup=kb)

    async def do_magic(callback, state=None):
        user_id = callback.from_user.id
        lang = await get_user_lang(user_id)
        phrases = lib(lang).MAGIC_PHRASES
        phrase = random.choice(phrases)
        while phrase == last_task["magic"].get(user_id) and len(phrases) > 1:
            phrase = random.choice(phrases)
        last_task["magic"][user_id] = phrase
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 One more" if lang == "en" else "🔁 Ещё одну", callback_data="magic_dust")],
            [InlineKeyboardButton(text="↩ Menu" if lang == "en" else "↩ В меню", callback_data="main_menu")]
        ])
        await callback.message.answer(phrase, reply_markup=kb)

    async def do_breathing(callback, state=None):
        user_lang = await get_user_lang(callback.from_user.id)
        text = "🧘 **Choose breathing technique:**\n\n🌊 **4-7-8**\n🌬️ **Equal breathing**\n🔥 **Fire breathing**" if user_lang == "en" else "🧘 **Выбери дыхательную практику:**\n\n🌊 **4-7-8**\n🌬️ **Равное дыхание**\n🔥 **Огненное дыхание**"
        await callback.message.answer(text, reply_markup=get_breathing_keyboard(user_lang), parse_mode="Markdown")

    PRACTICES = {"stalking": do_stalking, "shift": do_shift, "magic": do_magic, "breathing": do_breathing}

    @dp.message(Command("vtest"))
    async def vtest(message: types.Message):
        if message.from_user.id != 862373702:
            return
        await reset_voice_limit(message.from_user.id)
        await send_raven_voice(bot, message.from_user.id, "universal")

    @dp.message(Command("vreset"))
    async def vreset(message: types.Message):
        if message.from_user.id != 862373702:
            return
        await reset_voice_limit(message.from_user.id)
        await message.answer("🔓 Лимит голосовых сброшен. Теперь проверь практику.")

    # ПУТЬ СЕРДЦА · ПРАКТИКА ДНЯ
    @dp.callback_query(lambda c: c.data == "daily_practice")
    async def daily_practice(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        choice = random.choice(["stalking", "shift", "magic", "breathing"])
        lang = await get_user_lang(callback.from_user.id)
        await callback.message.answer("❤️ **Path of the Heart.**\n\nToday the Raven chose this practice for you:" if lang == "en" else "❤️ **Путь сердца.**\n\nСегодня Ворон выбрал для тебя эту практику:", parse_mode="Markdown")
        await PRACTICES[choice](callback, state)

    # ДНЕВНИК ВОИНА
    @dp.callback_query(lambda c: c.data == "warrior_diary")
    async def warrior_diary(callback: CallbackQuery):
        await callback.answer()
        lang = await get_user_lang(callback.from_user.id)
        rows = await get_stalking_entries(callback.from_user.id)
        if not rows:
            text = "📜 Your Stalker's Diary is still empty.\n\nThe first entry will appear after the practices «Stop the World» or «Path of the Heart»." if lang == "en" else "📜 Твой Дневник Сталкера пока пуст.\n\nПервая запись появится после практик «Остановить мир» или «Путь сердца»."
        else:
            lines = ["📜 Your Stalker's Diary:\n" if lang == "en" else "📜 Твой Дневник Сталкера:\n"]
            for i, r in enumerate(rows, 1):
                lines.append(f"🪶 #{i} · {r['date'][:10]}\n🎯 {r['task_text']}\n✍️ {r['user_response']}\n")
            text = "\n".join(lines)
        await callback.message.answer(text, reply_markup=back_kb(lang))

    # ОСТАНОВИТЬ МИР (диагностика)
    @dp.callback_query(lambda c: c.data == "diagnose_force")
    async def diagnose_force(callback: CallbackQuery):
        await callback.answer()
        lang = await get_user_lang(callback.from_user.id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌪 Irritation / Anger" if lang == "en" else "🌪 Раздражение / Злость", callback_data="diagnose_anger"),
             InlineKeyboardButton(text="🌫 Apathy / Emptiness" if lang == "en" else "🌫 Апатия / Пустота", callback_data="diagnose_apathy")],
            [InlineKeyboardButton(text="🏃 Rush / Thoughts" if lang == "en" else "🏃 Суета / Мысли", callback_data="diagnose_rush"),
             InlineKeyboardButton(text="🎭 Prove to someone" if lang == "en" else "🎭 Доказать кому-то", callback_data="diagnose_prove")]
        ])
        await callback.message.answer(lib(lang).DIAGNOSE_QUESTION, reply_markup=kb)

    @dp.callback_query(lambda c: c.data in ["diagnose_anger", "diagnose_apathy", "diagnose_rush", "diagnose_prove"])
    async def diagnose_answer(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        try:
            lang = await get_user_lang(callback.from_user.id)
            L = lib(lang)
            await bot.send_chat_action(callback.from_user.id, "typing")
            await asyncio.sleep(2.5)
            label = L.DIAGNOSE_LABELS[callback.data]
            fallback = L.DIAGNOSE_ANSWERS[callback.data] + "\n\n🦅 " + random.choice(L.DON_JUAN_QUOTES)
            text = await raven_ai(f"Воин признался, что его сейчас сильнее всего держит: {label}. Объясни по-вороньи, куда утекает его сила и как её вернуть. В конце добавь одну короткую мысль дона Хуана.", fallback, lang)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪶 Fix the intention" if lang == "en" else "🪶 Закрепить намерение", callback_data="diagnose_commit")],
                [InlineKeyboardButton(text="↩ Menu" if lang == "en" else "↩ В меню", callback_data="main_menu")]
            ])
            pending["task"][callback.from_user.id] = ("🌑 Stop the World: " if lang == "en" else "🌑 Остановить мир: ") + label
            await state.set_state(StalkingStates.waiting_answer)
            await callback.message.answer(text, reply_markup=kb)
            await send_raven_voice(bot, callback.from_user.id, "diagnose")
        except Exception as e:
            err(e, "diagnose_answer")

    @dp.callback_query(lambda c: c.data == "diagnose_commit")
    async def diagnose_commit(callback: CallbackQuery):
        await callback.answer()
        lang = await get_user_lang(callback.from_user.id)
        await callback.message.answer("🦅 Write your intention in one phrase.\n\nFor example: «Today I will not justify myself» or «I let go of my resentment toward...»" if lang == "en" else "🦅 Напиши своё намерение одной фразой.\n\nНапример: «Сегодня я не буду оправдываться» или «Я отпускаю обиду на...»")

    # ЩЕПОТКА МАГИИ
    @dp.callback_query(lambda c: c.data == "magic_dust")
    async def magic_dust(callback: CallbackQuery):
        await callback.answer()
        await do_magic(callback)
        await send_raven_voice(bot, callback.from_user.id, "magic")

    # СДВИНУТЬ ВОСПРИЯТИЕ
    @dp.callback_query(lambda c: c.data == "shift_assembly")
    async def shift_assembly(callback: CallbackQuery):
        await callback.answer()
        await do_shift(callback)

    @dp.callback_query(lambda c: c.data == "shift_done")
    async def shift_done(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        try:
            lang = await get_user_lang(callback.from_user.id)
            await bot.send_chat_action(callback.from_user.id, "typing")
            await asyncio.sleep(2)
            user_id = callback.from_user.id
            pending["task"][user_id] = "🌀 Shift perception" if lang == "en" else "🌀 Сдвинуть восприятие"
            await state.set_state(StalkingStates.waiting_answer)
            fallback = "You shifted the assemblage point. The world is no longer what it was this morning." if lang == "en" else "Ты сдвинул точку сборки. Мир уже не тот, что был утром."
            text = await raven_ai("Воин выполнил практику сдвига восприятия и нажал «Я сделал это». Откликнись по-вороньи, коротко (2-3 предложения), как проводник.", fallback, lang)
            await callback.message.answer(text + ("\n\nTell me: what did you feel? What did you notice? Write below." if lang == "en" else "\n\nРасскажи: что ты ощутил? Что заметил? Напиши ниже."))
        except Exception as e:
            err(e, "shift_done")

    # ВЫСЛЕДИТЬ СЕБЯ
    @dp.callback_query(lambda c: c.data == "stalking_start")
    async def stalking_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await do_stalking(callback, state)

    @dp.message(StalkingStates.waiting_answer, F.text & ~F.text.startswith("/"))
    async def stalking_answer(message: types.Message, state: FSMContext):
        try:
            user_id = message.from_user.id
            lang = await get_user_lang(user_id)
            pending["response"][user_id] = message.text
            await bot.send_chat_action(message.from_user.id, "typing")
            await asyncio.sleep(2.5)
            task = pending["task"].get(user_id, "")
            fallback = ("You stopped and saw. That is already a victory.\nMost people pass through life without blinking, but you stopped and saw." if lang == "en" else "Ты заметил ловушку. Это уже победа.\nБольшинство людей проходят сквозь жизнь, даже не моргнув, а ты остановился и увидел.")
            reaction = await raven_ai(f"Воин выполнял практику («{task}») и поделился опытом: «{message.text}». Откликнись по-вороньи: признай, что он остановился и увидел. 2-4 предложения.", fallback, lang)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Yes, save" if lang == "en" else "📜 Да, сохранить", callback_data="stalking_save")],
                [InlineKeyboardButton(text="↩ No, let's go" if lang == "en" else "↩ Нет, идём дальше", callback_data="stalking_skip")]
            ])
            await message.answer(reaction + ("\n\nSave this entry to your Stalker's Diary?" if lang == "en" else "\n\nСохранить эту запись в твой Дневник Сталкера?"), reply_markup=kb)
        except Exception as e:
            err(e, "stalking_answer")

    @dp.callback_query(lambda c: c.data == "stalking_save")
    async def stalking_save(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        try:
            user_id = callback.from_user.id
            lang = await get_user_lang(user_id)
            await save_stalking_entry(user_id, pending["task"].get(user_id, ""), pending["response"].get(user_id, ""))
            await state.clear()
            task = pending["task"].get(user_id, "")
            trig = "practice" if (task.startswith("🌀") or task.startswith("🌬️")) else ("stop_world" if task.startswith("🌑") else "diary")
            await send_raven_voice(bot, user_id, trig)
            await callback.message.answer(with_ps("Entry saved. You will be able to return to it and see how you change.\n\nWalk on, warrior. 🪶" if lang == "en" else "Запись сохранена. Ты сможешь вернуться к ней и увидеть, как меняешься.\n\nИди дальше, воин. 🪶", callback.from_user, lang), reply_markup=back_kb(lang))
        except Exception as e:
            err(e, "stalking_save")

    @dp.callback_query(lambda c: c.data == "stalking_skip")
    async def stalking_skip(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.clear()
        user_lang = await get_user_lang(callback.from_user.id)
        await callback.message.answer("🦅 **Main menu:**" if user_lang == "en" else "🦅 **Главное меню:**", reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")

    # ИНДУЛЬГИМЕТР
    @dp.callback_query(lambda c: c.data == "indulgimeter_start")
    async def indulgi_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.clear()
        lang = await get_user_lang(callback.from_user.id)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="▶️ Start the test" if lang == "en" else "▶️ Начать тест", callback_data="indulgi_begin")]])
        await callback.message.answer("⚖️ **Indulgimeter**\n\nIndulging is self-justification, self-pity, «it's not my fault, it's circumstances». A warrior doesn't indulge. He takes responsibility.\n\nAnswer 5 questions honestly. I will count how much you feed your importance." if lang == "en" else "⚖️ **Индульгиметр**\n\nИндульгирование — это самооправдание, жалость к себе, «я не виноват, это обстоятельства». Воин не индульгирует. Он берёт ответственность.\n\nОтветь на 5 вопросов честно. Я посчитаю, насколько ты кормишь свою важность.", reply_markup=kb, parse_mode="Markdown")

    @dp.callback_query(lambda c: c.data == "indulgi_begin")
    async def indulgi_begin(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        lang = await get_user_lang(callback.from_user.id)
        await state.set_state(IndulgiStates.q1)
        await state.update_data(score=0)
        await callback.message.answer(f"**Question 1/5**\n\n{lib(lang).INDULGI_QUESTIONS[0]['text']}" if lang == "en" else f"**Вопрос 1/5**\n\n{lib(lang).INDULGI_QUESTIONS[0]['text']}", reply_markup=indulgi_kb(1, lang), parse_mode="Markdown")

    @dp.callback_query(lambda c: c.data.startswith("indulgi_q"))
    async def indulgi_answer(callback: CallbackQuery, state: FSMContext):
        cur = await state.get_state()
        if cur is None:
            await callback.answer("The test is over. Start again: ⚖️ Indulgimeter" if (await get_user_lang(callback.from_user.id)) == "en" else "Тест завершён. Начни заново: ⚖️ Индульгиметр")
            return
        await callback.answer()
        try:
            lang = await get_user_lang(callback.from_user.id)
            L = lib(lang)
            parts = callback.data.split("_")
            n = int(parts[1][1:])
            q = L.INDULGI_QUESTIONS[n - 1]
            score_add = next(o["score"] for o in q["options"] if o["callback"] == callback.data)
            data = await state.get_data()
            score = data.get("score", 0) + score_add
            if n < 5:
                await state.update_data(score=score)
                await state.set_state(getattr(IndulgiStates, f"q{n + 1}"))
                await callback.message.answer(("**Question " if lang == "en" else "**Вопрос ") + f"{n + 1}/5**\n\n{L.INDULGI_QUESTIONS[n]['text']}", reply_markup=indulgi_kb(n + 1, lang), parse_mode="Markdown")
            else:
                await state.clear()
                await save_indulgi_score(callback.from_user.id, score)
                await bot.send_chat_action(callback.from_user.id, "typing")
                await asyncio.sleep(2.5)
                if score <= 2:
                    res = "You almost never indulge.\n\nYour assemblage point is stable. You walk the warrior's path. Don't relax — death is on the left." if lang == "en" else "Ты почти не индульгируешь.\n\nТвоя точка сборки устойчива. Ты идёшь путём воина. Не расслабляйся, смерть слева."
                elif score <= 6:
                    res = "🪶 You see your traps, but sometimes step into them.\n\nYou are on the path, but the moths still buzz. Practice stalking." if lang == "en" else "🪶 Ты видишь свои ловушки, но иногда наступаешь в них.\n\nТы на пути, но мотыльки всё ещё жужжат. Практикуй выслеживание."
                else:
                    res = "💀 You live in indulging.\n\nYou feed your importance to the full. Death doesn't wait until you stop pitying yourself. Stop. Right now." if lang == "en" else "💀 Ты живёшь в индульгировании.\n\nТы кормишь свою важность до отвала. Смерть не ждёт, пока ты перестанешь себя жалеть. Остановись. Прямо сейчас."
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Take it again" if lang == "en" else "🔄 Пройти ещё раз", callback_data="indulgimeter_start")],
                    [InlineKeyboardButton(text="↩ Menu" if lang == "en" else "↩ В меню", callback_data="main_menu")]
                ])
                await callback.message.answer(with_ps(("**Your result: " if lang == "en" else "**Твой результат: ") + f"{score} / 10**\n\n{res}", callback.from_user, lang), reply_markup=kb, parse_mode="Markdown")
                await send_raven_voice(bot, callback.from_user.id, "indulgi_low" if score <= 2 else ("indulgi_mid" if score <= 6 else "indulgi_high"))
        except Exception as e:
            err(e, "indulgi_answer")

    # ДЫХАНИЕ С РЕФЛЕКСИЕЙ
    @dp.callback_query(lambda c: c.data.startswith("breathe_"))
    async def breathing_exercise(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        user_id = callback.from_user.id
        exercise = callback.data.replace("breathe_", "")
        user_lang = await get_user_lang(user_id)
        names = {"478": "4-7-8", "equal": "Equal breathing", "fire": "Fire breathing"} if user_lang == "en" else {"478": "4-7-8", "equal": "Равное дыхание", "fire": "Огненное дыхание"}
        exercises_ru = {"478": "**Техника 4-7-8**\n\n1. Вдох — 4 сек\n2. Задержка — 7 сек\n3. Выдох — 8 сек\n\nПовтори 4 раза. 💤", "equal": "🌬️ **Равное дыхание**\n\n1. Вдох — 4 сек\n2. Выдох — 4 сек\n\nПовтори 5-10 раз. ⚖️", "fire": "🔥 **Огненное дыхание**\n\nРезкий выдох через нос, вдох автоматически. Темп: 1-2 цикла в сек. Делай 30 сек. ⚡"}
        exercises_en = {"478": "**4-7-8 Technique**\n\n1. Inhale — 4s\n2. Hold — 7s\n3. Exhale — 8s\n\nRepeat 4 times. 💤", "equal": "🌬️ **Equal Breathing**\n\n1. Inhale — 4s\n2. Exhale — 4s\n\nRepeat 5-10 times. ⚖️", "fire": "🔥 **Fire Breathing**\n\nSharp exhale through nose, inhale automatically. Pace: 1-2 cycles/sec. Do for 30s. ⚡"}
        exercises = exercises_en if user_lang == "en" else exercises_ru
        pending["task"][user_id] = ("🌬️ Breathing: " if user_lang == "en" else "🌬️ Дыхание: ") + names.get(exercise, "")
        await state.set_state(StalkingStates.waiting_answer)
        await callback.message.answer(exercises.get(exercise, "Choose an exercise."), parse_mode="Markdown")
        await callback.message.answer("🦅 When done — tell me: what did you feel? What did you notice? Write below." if user_lang == "en" else "🦅 Когда выполнишь — расскажи: что ты ощутил? Что заметил? Напиши ниже.")