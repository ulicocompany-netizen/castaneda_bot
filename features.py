# ============================================
# FEATURES.PY v4 — ИИ-ВОРОН «ПУТЬ ВОИНА»
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
from openai import AsyncOpenAI

from keyboards import get_main_menu_keyboard, get_breathing_keyboard
from database import get_user_lang
from voices import send_raven_voice, reset_voice_limit
from aiogram.filters import Command

DB_PATH = "bot.db"

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

RAVEN_SYSTEM = "Ты — Ворон, проводник по пути воина в стиле учения Карлоса Кастанеды. Говори хрипло, спокойно, без «успешного успеха» и без штампов психологических курсов. Используй образы учения дона Хуана: смерть как советчик, точка сборки, мотыльки внутреннего диалога, важность, безупречность, остановка мира, путь с сердцем, тональ и нагваль. Отвечай КОРОТКО: 3-6 предложений, без списков и заголовков. Обращайся на «ты»: воин, путник, или по имени, если оно известно."

class StalkingStates(StatesGroup):
    waiting_answer = State()

class IndulgiStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()

# ---------- БИБЛИОТЕКИ (запасной вариант, если ИИ недоступен) ----------
STALKING_TASKS = [
    "Сегодня твоя добыча — твои слова. Замечай каждый раз, когда ты говоришь «я должен» или «мне придётся». Не меняй это. Просто поймай себя на этом слове и спроси: «Кто это говорит? Воин или жертва?»\n\nНапиши мне ниже, сколько раз ты попался в эту ловушку сегодня, или опиши один такой момент.",
    "Твоя задача на сегодня — выследить свою жалость к себе. Каждый раз, когда ты начинаешь думать «бедный я, как же мне не повезло» — остановись. Запиши этот момент.\n\nНапиши мне, сколько раз ты поймал себя на этом, или опиши один случай.",
    "Сегодня следи за своим внутренним диалогом. Когда ты начинаешь спорить с собой, оправдываться или ругать себя — заметь это. Это мотыльки жужжат.\n\nНапиши мне, в какой момент ты услышал их громче всего.",
    "Твоя добыча сегодня — твои реакции. Когда кто-то скажет или сделает что-то, что тебя заденет — не реагируй сразу. Досчитай до трёх. Потом реши, стоит ли отвечать.\n\nНапиши мне, сколько раз ты успел остановиться, а сколько раз повёлся.",
    "Сегодня выслеживай свою важность. Каждый раз, когда ты думаешь «а что обо мне подумают» или «я должен показать, что я...» — заметь это. Это корона, которую ты несёшь.\n\nНапиши мне, сколько раз ты поймал себя на этом."
]

SHIFT_TASKS = [
    "🌀 Точка сборки сдвигается там, где ломается привычка.\n\nСегодня сделай одно привычное действие непривычной рукой. Почисти зубы, открой дверь или возьми чашку. Почувствуй, как мир на секунду стал чужим и новым. Это и есть магия.",
    "🌀 Твой тональ привык смотреть под ноги.\n\nСегодня, идя по знакомой дороге, смотри только вверх. На ветви, на облака, на линии крыш. Не смотри на асфальт. Заметь, сколько деталей ты обычно игнорируешь.",
    "🌀 Сделай что-то сегодня намеренно медленно.\n\nТо, что ты обычно делаешь в спешке (ешь, идёшь, отвечаешь на сообщение). Растяни время. Почувствуй сопротивление своего ума, который торопится. Останови его.",
    "🌀 Сновидение — это сдвиг точки сборки во сне.\n\nСегодня перед сном намерься увидеть свои руки во сне. Скажи себе: «Я увижу свои руки». Утром запиши, получилось ли.",
    "🌀 Твоё восприятие привыкло к определённым маршрутам.\n\nСегодня пойди домой другой дорогой. Даже если это займёт больше времени. Почувствуй, как мир становится новым.",
    "🌀 Ты привык говорить «да» или «нет» автоматически.\n\nСегодня перед каждым ответом делай паузу в 2 секунды. Почувствуй, как это меняет разговор."
]

MAGIC_PHRASES = [
    "🔮 Смерть стоит за твоим левым плечом. Иди сегодня так, будто это твой последний танец. Легко и безупречно.",
    "🔮 Твоё намерение на сегодня: не кормить важность. Ни разу. Даже в мелочах.",
    "🔮 Сегодня ты увидишь знак. Не пытайся его разгадать умом. Просто заметь его и иди дальше.",
    "🔮 Путь с сердцем — это тот путь, где ты не тащишь себя. Если сегодня что-то идёт тяжело, спроси: «Есть ли у этого пути сердце?»",
    "🔮 Сегодня вечером посмотри на звёзды. Напомни себе, как ты мал в этой вселенной. Это не унижает. Это освобождает.",
    "🔮 Твоё намерение: действовать, а не готовиться действовать. Сделай один шаг, который откладывал.",
    "🔮 Сегодня не ищи лёгкий путь. Ищи путь воина. Он не легче, но он твой.",
    "🔮 Помни: ты не то, что ты думаешь. Ты то, что ты делаешь, когда не думаешь.",
    "🔮 Сегодня твой советчик — тишина. Слушай её чаще, чем свой ум.",
    "🔮 Не бойся потерять то, что ты не выбирал. Корона, которую ты не надевал, не твоя."
]

DON_JUAN_QUOTES = [
    "Смерть — единственный мудрый советник. Когда жизнь кажется тяжёлой, спроси её. Она ответит: ничего не имеет значения, кроме её прикосновения.",
    "Безупречность — это не мораль. Это экономия силы.",
    "Воин берёт ответственность за свои поступки, даже за самые малые.",
    "Стирание личной истории освобождает тебя от чужих ожиданий.",
    "Мир непостижим. Он тайна. И ты — тайна в нём.",
    "Путь с сердцем лёгок; не нужно усилий, чтобы любить его.",
    "Действовать без ожидания награды — вот делание воина.",
    "Жалость к себе — самый тяжёлый груз. Сбрось его, и ты почувствуешь лёгкость.",
    "Точка сборки сдвигается, когда воин перестаёт разговаривать с собой.",
    "Не-делание — ключ к остановке мира.",
    "Сила не требует веры. Она требует внимания.",
    "Ты не история своих мыслей. Ты — внимание, которое их наблюдает."
]

PS_LINES = [
    "P.S. Хорошо. Ты сделал это. Иди дальше.",
    "P.S. Я вижу, ты стараешься. Не будь строг к себе.",
    "P.S. Мотыльки стихли? Отлично.",
    "P.S. Смерть кивает. Ты сегодня был честен.",
    "P.S. Не рассказывай об этом никому. Сила любит тишину."
]

PS_NAME_LINES = [
    "P.S. {name}, мотыльки стихли? Отлично.",
    "P.S. {name}, сила не спрашивает имени. Она спрашивает намерения.",
    "P.S. {name}, ты снова здесь. Это уже путь."
]

DIAGNOSE_QUESTION = "🦅 Сила не исчезает бесследно. Она утекает туда, где ты кормишь свою важность или индульгируешь.\n\nПосмотри внутрь прямо сейчас. Что из этого отзывается в тебе сильнее всего?"

DIAGNOSE_LABELS = {
    "diagnose_anger": "раздражение и злость",
    "diagnose_apathy": "апатия и пустота",
    "diagnose_rush": "суета и бегущие мысли",
    "diagnose_prove": "желание доказать кому-то"
}

DIAGNOSE_ANSWERS = {
    "diagnose_anger": "Раздражение — это стена. Ты строишь её, потому что боишься, что твою важность заденут.\nНо стена тоже требует силы на поддержание.\nОпусти её. Посмотри на то, что тебя злит, просто как на факт. Как на камень на дороге. Без оценки. Сила вернётся, как только ты перестанешь с этим бороться.",
    "diagnose_apathy": "Ты думаешь, что теряешь силу. Но пустота — это не отсутствие силы. Это тишина перед сдвигом.\nОшибка — пытаться заполнить эту тишину шумом, скроллингом или суетой.\nНе убегай от неё. Побудь в ней. Это и есть та самая остановка мира, которую ты ищешь.",
    "diagnose_rush": "Мотыльки жужжат. Ты пытаешься контролировать то, что контролю не подлежит — свой ум.\nЧем сильнее ты пытаешься их прогнать, тем жирнее они становятся.\nОтпусти поводья. Пусть мысли крутятся, как листья на ветру, но не цепляй их. Просто наблюдай, как они пролетают мимо.",
    "diagnose_prove": "Ты тратишь самую дорогую валюту на воображаемого зрителя.\nНапомни себе: смерть стоит за твоим левым плечом. Ей абсолютно всё равно, прав ты или нет, одобряют тебя или нет.\nДействуй только для себя. Всё остальное — корм для мотыльков."
}

INDULGI_QUESTIONS = [
    {"text": "Когда твои планы рушатся, твоя первая реакция:", "options": [
        {"text": "Ищу, кто виноват, или жалею себя", "score": 2, "callback": "indulgi_q1_a"},
        {"text": "Злюсь, но быстро беру себя в руки", "score": 1, "callback": "indulgi_q1_b"},
        {"text": "Спокойно меняю тактику. Это просто новые обстоятельства", "score": 0, "callback": "indulgi_q1_c"}]},
    {"text": "Как часто ты даёшь обещания, которые не выполняешь (даже себе)?", "options": [
        {"text": "Часто. Обстоятельства всегда сильнее", "score": 2, "callback": "indulgi_q2_a"},
        {"text": "Иногда, но я нахожу этому оправдание", "score": 1, "callback": "indulgi_q2_b"},
        {"text": "Почти никогда. Моё слово — это моя сила", "score": 0, "callback": "indulgi_q2_c"}]},
    {"text": "Когда тебя критикуют, ты:", "options": [
        {"text": "Защищаюсь или обижаюсь", "score": 2, "callback": "indulgi_q3_a"},
        {"text": "Делаю вид, что мне всё равно, но внутри киплю", "score": 1, "callback": "indulgi_q3_b"},
        {"text": "Слушаю. Если полезно — беру, если нет — отсекаю", "score": 0, "callback": "indulgi_q3_c"}]},
    {"text": "Чувствуешь ли ты, что мир «должен» тебе справедливость или понимание?", "options": [
        {"text": "Да, постоянно", "score": 2, "callback": "indulgi_q4_a"},
        {"text": "Иногда, когда мне тяжело", "score": 1, "callback": "indulgi_q4_b"},
        {"text": "Нет. Мир не должен мне ничего. Я беру то, что могу", "score": 0, "callback": "indulgi_q4_c"}]},
    {"text": "Твоя усталость в конце дня — это чаще:", "options": [
        {"text": "Результат бесконечных внутренних диалогов и тревог", "score": 2, "callback": "indulgi_q5_a"},
        {"text": "Смесь реальных дел и эмоциональной тряски", "score": 1, "callback": "indulgi_q5_b"},
        {"text": "Результат реальных, но безупречных действий. Я спокоен", "score": 0, "callback": "indulgi_q5_c"}]}
]

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
def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩ В меню", callback_data="main_menu")]])

def indulgi_kb(n):
    rows = [[InlineKeyboardButton(text=o["text"], callback_data=o["callback"])] for o in INDULGI_QUESTIONS[n - 1]["options"]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def with_ps(text, user=None):
    if random.random() < 0.3:
        name = getattr(user, "first_name", None)
        if name and random.random() < 0.5:
            text += "\n\n" + random.choice(PS_NAME_LINES).format(name=name)
        else:
            text += "\n\n" + random.choice(PS_LINES)
    return text

def err(e, where):
    print(f"❌ ОШИБКА ФИЧИ [{where}]: {e}")
    traceback.print_exc()

async def raven_ai(user_prompt, fallback):
    """ИИ-Ворон: уникальный ответ в стиле Кастанеды. Если API недоступен — запасной текст."""
    try:
        r = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": RAVEN_SYSTEM}, {"role": "user", "content": user_prompt}],
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
        task = random.choice(STALKING_TASKS)
        while task == last_task["stalking"].get(user_id) and len(STALKING_TASKS) > 1:
            task = random.choice(STALKING_TASKS)
        last_task["stalking"][user_id] = task
        pending["task"][user_id] = task
        await callback.message.answer(f"🦅 Ворон наблюдает.\n\n{task}")
        await state.set_state(StalkingStates.waiting_answer)

    async def do_shift(callback, state=None):
        user_id = callback.from_user.id
        task = random.choice(SHIFT_TASKS)
        while task == last_task["shift"].get(user_id) and len(SHIFT_TASKS) > 1:
            task = random.choice(SHIFT_TASKS)
        last_task["shift"][user_id] = task
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я сделал это", callback_data="shift_done")],
            [InlineKeyboardButton(text="↩ В меню", callback_data="main_menu")]
        ])
        await callback.message.answer(f"{task}\n\nКогда выполнишь — нажми кнопку ниже.", reply_markup=kb)

    async def do_magic(callback, state=None):
        user_id = callback.from_user.id
        phrase = random.choice(MAGIC_PHRASES)
        while phrase == last_task["magic"].get(user_id) and len(MAGIC_PHRASES) > 1:
            phrase = random.choice(MAGIC_PHRASES)
        last_task["magic"][user_id] = phrase
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Ещё одну", callback_data="magic_dust")],
            [InlineKeyboardButton(text="↩ В меню", callback_data="main_menu")]
        ])
        await callback.message.answer(phrase, reply_markup=kb)
        await send_raven_voice(bot, user_id, "magic")

    async def do_breathing(callback, state=None):
        user_lang = await get_user_lang(callback.from_user.id)
        text = "🧘 **Выбери дыхательную практику:**\n\n🌊 **4-7-8**\n🌬️ **Равное дыхание**\n🔥 **Огненное дыхание**" if user_lang == "ru" else "🧘 **Choose breathing technique:**\n\n🌊 **4-7-8**\n🌬️ **Equal breathing**\n🔥 **Fire breathing**"
        await callback.message.answer(text, reply_markup=get_breathing_keyboard(user_lang), parse_mode="Markdown")

    PRACTICES = {"stalking": do_stalking, "shift": do_shift, "magic": do_magic, "breathing": do_breathing}

    # ДЫХАНИЕ С РЕФЛЕКСИЕЙ (теперь тоже ведёт в дневник)
    @dp.callback_query(lambda c: c.data.startswith("breathe_"))
    async def breathing_exercise(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        user_id = callback.from_user.id
        exercise = callback.data.replace("breathe_", "")
        user_lang = await get_user_lang(user_id)
        names = {"478": "4-7-8", "equal": "Равное дыхание", "fire": "Огненное дыхание"} if user_lang == "ru" else {"478": "4-7-8", "equal": "Equal breathing", "fire": "Fire breathing"}
        exercises_ru = {"478": "**Техника 4-7-8**\n\n1. Вдох — 4 сек\n2. Задержка — 7 сек\n3. Выдох — 8 сек\n\nПовтори 4 раза. 💤", "equal": "🌬️ **Равное дыхание**\n\n1. Вдох — 4 сек\n2. Выдох — 4 сек\n\nПовтори 5-10 раз. ⚖️", "fire": "🔥 **Огненное дыхание**\n\nРезкий выдох через нос, вдох автоматически. Темп: 1-2 цикла в сек. Делай 30 сек. ⚡"}
        exercises_en = {"478": "**4-7-8 Technique**\n\n1. Inhale — 4s\n2. Hold — 7s\n3. Exhale — 8s\n\nRepeat 4 times. 💤", "equal": "🌬️ **Equal Breathing**\n\n1. Inhale — 4s\n2. Exhale — 4s\n\nRepeat 5-10 times. ⚖️", "fire": "🔥 **Fire Breathing**\n\nSharp exhale through nose, inhale automatically. Pace: 1-2 cycles/sec. Do for 30s. ⚡"}
        exercises = exercises_en if user_lang == "en" else exercises_ru
        pending["task"][user_id] = f"🌬️ Дыхание: {names.get(exercise, '')}"
        await state.set_state(StalkingStates.waiting_answer)
        await callback.message.answer(exercises.get(exercise, "Выбери упражнение."), parse_mode="Markdown")
        await callback.message.answer("🦅 Когда выполнишь — расскажи: что ты ощутил? Что заметил? Напиши ниже.")

    # ПУТЬ СЕРДЦА · ПРАКТИКА ДНЯ
    @dp.callback_query(lambda c: c.data == "daily_practice")
    async def daily_practice(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        choice = random.choice(["stalking", "shift", "magic", "breathing"])
        await callback.message.answer("❤️ **Путь сердца.**\n\nСегодня Ворон выбрал для тебя эту практику:" if (await get_user_lang(callback.from_user.id)) == "ru" else "❤️ **Path of the Heart.**\n\nToday the Raven chose this practice for you:", parse_mode="Markdown")
        await PRACTICES[choice](callback, state)

    # ДНЕВНИК ВОИНА
    @dp.callback_query(lambda c: c.data == "warrior_diary")
    async def warrior_diary(callback: CallbackQuery):
        await callback.answer()
        rows = await get_stalking_entries(callback.from_user.id)
        if not rows:
            text = "📜 Твой Дневник Сталкера пока пуст.\n\nПервая запись появится после практики «Выследить себя» или «Остановить мир»."
        else:
            lines = ["📜 Твой Дневник Сталкера :\n"]
            for r in rows:
                lines.append(f"{r['date'][:10]}\n🎯 {r['task_text']}\n✍️ {r['user_response']}\n")
            text = "\n".join(lines)
        await callback.message.answer(text, reply_markup=back_kb())

    # ОСТАНОВИТЬ МИР (диагностика силы)
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

    @dp.callback_query(lambda c: c.data == "diagnose_force")
    async def diagnose_force(callback: CallbackQuery):
        await callback.answer()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌪 Раздражение / Злость", callback_data="diagnose_anger"),
             InlineKeyboardButton(text="🌫 Апатия / Пустота", callback_data="diagnose_apathy")],
            [InlineKeyboardButton(text="🏃 Суета / Мысли", callback_data="diagnose_rush"),
             InlineKeyboardButton(text="🎭 Доказать кому-то", callback_data="diagnose_prove")]
        ])
        await callback.message.answer(DIAGNOSE_QUESTION, reply_markup=kb)

    @dp.callback_query(lambda c: c.data in ["diagnose_anger", "diagnose_apathy", "diagnose_rush", "diagnose_prove"])
    async def diagnose_answer(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        try:
            await bot.send_chat_action(callback.from_user.id, "typing")
            await asyncio.sleep(2.5)
            label = DIAGNOSE_LABELS[callback.data]
            fallback = DIAGNOSE_ANSWERS[callback.data] + "\n\n🦅 " + random.choice(DON_JUAN_QUOTES)
            text = await raven_ai(f"Воин признался, что его сейчас сильнее всего держит: {label}. Объясни ему по-вороньи, куда утекает его сила и как её вернуть. В конце добавь одну короткую мысль дона Хуана.", fallback)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪶 Закрепить намерение", callback_data="diagnose_commit")],
                [InlineKeyboardButton(text="↩ В меню", callback_data="main_menu")]
            ])
            pending["task"][callback.from_user.id] = f"🌑 Остановить мир: {label}"
            await state.set_state(StalkingStates.waiting_answer)
            await callback.message.answer(text, reply_markup=kb)
            await send_raven_voice(bot, callback.from_user.id, "diagnose")
        except Exception as e:
            err(e, "diagnose_answer")

    @dp.callback_query(lambda c: c.data == "diagnose_commit")
    async def diagnose_commit(callback: CallbackQuery):
        await callback.answer()
        await callback.message.answer("🦅 Напиши своё намерение одной фразой.\n\nНапример: «Сегодня я не буду оправдываться» или «Я отпускаю обиду на...»")

    # ЩЕПОТКА МАГИИ
    @dp.callback_query(lambda c: c.data == "magic_dust")
    async def magic_dust(callback: CallbackQuery):
        await callback.answer()
        await do_magic(callback)

    # СДВИНУТЬ ВОСПРИЯТИЕ
    @dp.callback_query(lambda c: c.data == "shift_assembly")
    async def shift_assembly(callback: CallbackQuery):
        await callback.answer()
        await do_shift(callback)

    @dp.callback_query(lambda c: c.data == "shift_done")
    async def shift_done(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        try:
            await bot.send_chat_action(callback.from_user.id, "typing")
            await asyncio.sleep(2)
            user_id = callback.from_user.id
            pending["task"][user_id] = "🌀 Сдвинуть восприятие"
            await state.set_state(StalkingStates.waiting_answer)
            fallback = "Ты сдвинул точку сборки. Мир уже не тот, что был утром."
            text = await raven_ai("Воин выполнил практику сдвига восприятия и нажал «Я сделал это». Откликнись по-вороньи, коротко (2-3 предложения), как проводник.", fallback)
            await callback.message.answer(text + "\n\nРасскажи: что ты ощутил? Что заметил? Напиши ниже.")
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
            pending["response"][user_id] = message.text
            await bot.send_chat_action(message.from_user.id, "typing")
            await asyncio.sleep(2.5)
            task = pending["task"].get(user_id, "")
            fallback = "Ты заметил ловушку. Это уже победа.\nБольшинство людей проходят сквозь жизнь, даже не моргнув, а ты остановился и увидел."
            reaction = await raven_ai(f"Воин выполнял практику («{task}») и поделился опытом: «{message.text}». Откликнись по-вороньи: признай, что он остановился и увидел. 2-4 предложения.", fallback)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Да, сохранить", callback_data="stalking_save")],
                [InlineKeyboardButton(text="↩ Нет, идём дальше", callback_data="stalking_skip")]
            ])
            await message.answer(reaction + "\n\nСохранить эту запись в твой Дневник Сталкера?", reply_markup=kb)
        except Exception as e:
            err(e, "stalking_answer")

    @dp.callback_query(lambda c: c.data == "stalking_save")
    async def stalking_save(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        try:
            user_id = callback.from_user.id
            await save_stalking_entry(user_id, pending["task"].get(user_id, ""), pending["response"].get(user_id, ""))
            await state.clear()
            task = pending["task"].get(user_id, "")
            trig = "practice" if (task.startswith("🌀") or task.startswith("🌬️")) else ("stop_world" if task.startswith("🌑") else "diary")
            await send_raven_voice(bot, user_id, trig)
            await callback.message.answer(with_ps("Запись сохранена. Ты сможешь вернуться к ней и увидеть, как меняешься.\n\nИди дальше, воин. 🪶", callback.from_user), reply_markup=back_kb())
        except Exception as e:
            err(e, "stalking_save")

    @dp.callback_query(lambda c: c.data == "stalking_skip")
    async def stalking_skip(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.clear()
        user_lang = await get_user_lang(callback.from_user.id)
        await callback.message.answer("🦅 **Главное меню:**" if user_lang == "ru" else "🦅 **Main menu:**", reply_markup=get_main_menu_keyboard(user_lang), parse_mode="Markdown")

    # ИНДУЛЬГИМЕТР
    @dp.callback_query(lambda c: c.data == "indulgimeter_start")
    async def indulgi_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.clear()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="▶️ Начать тест", callback_data="indulgi_begin")]])
        await callback.message.answer("⚖️ **Индульгиметр**\n\nИндульгирование — это самооправдание, жалость к себе, «я не виноват, это обстоятельства». Воин не индульгирует. Он берёт ответственность.\n\nОтветь на 5 вопросов честно. Я посчитаю, насколько ты кормишь свою важность.", reply_markup=kb, parse_mode="Markdown")

    @dp.callback_query(lambda c: c.data == "indulgi_begin")
    async def indulgi_begin(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.set_state(IndulgiStates.q1)
        await state.update_data(score=0)
        await callback.message.answer(f"**Вопрос 1/5**\n\n{INDULGI_QUESTIONS[0]['text']}", reply_markup=indulgi_kb(1), parse_mode="Markdown")

    @dp.callback_query(lambda c: c.data.startswith("indulgi_q"))
    async def indulgi_answer(callback: CallbackQuery, state: FSMContext):
        cur = await state.get_state()
        if cur is None:
            await callback.answer("Тест завершён. Начни заново: ⚖️ Индульгиметр")
            return
        await callback.answer()
        try:
            parts = callback.data.split("_")
            n = int(parts[1][1:])
            q = INDULGI_QUESTIONS[n - 1]
            score_add = next(o["score"] for o in q["options"] if o["callback"] == callback.data)
            data = await state.get_data()
            score = data.get("score", 0) + score_add
            if n < 5:
                await state.update_data(score=score)
                await state.set_state(getattr(IndulgiStates, f"q{n + 1}"))
                await callback.message.answer(f"**Вопрос {n + 1}/5**\n\n{INDULGI_QUESTIONS[n]['text']}", reply_markup=indulgi_kb(n + 1), parse_mode="Markdown")
            else:
                await state.clear()
                await save_indulgi_score(callback.from_user.id, score)
                await bot.send_chat_action(callback.from_user.id, "typing")
                await asyncio.sleep(2.5)
                if score <= 2:
                    res = "Ты почти не индульгируешь.\n\nТвоя точка сборки устойчива. Ты идёшь путём воина. Не расслабляйся, смерть слева."
                elif score <= 6:
                    res = "🪶 Ты видишь свои ловушки, но иногда наступаешь в них.\n\nТы на пути, но мотыльки всё ещё жужжат. Практикуй выслеживание."
                else:
                    res = "💀 Ты живёшь в индульгировании.\n\nТы кормишь свою важность до отвала. Смерть не ждёт, пока ты перестанешь себя жалеть. Остановись. Прямо сейчас."
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Пройти ещё раз", callback_data="indulgimeter_start")],
                    [InlineKeyboardButton(text="↩ В меню", callback_data="main_menu")]
                ])
                await callback.message.answer(with_ps(f"**Твой результат: {score} из 10**\n\n{res}", callback.from_user), reply_markup=kb, parse_mode="Markdown")
                await send_raven_voice(bot, callback.from_user.id, "indulgi_low" if score <= 2 else ("indulgi_mid" if score <= 6 else "indulgi_high"))
        except Exception as e:
            err(e, "indulgi_answer")