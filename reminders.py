import random

REMINDERS_RU = [
    "🌑 **Воин помнит о смерти**\n\n"
    "Смерть стоит за твоим левым плечом. Она может коснуться тебя в любой момент.\n\n"
    "Если бы ты знал, что сегодня последний день — стал бы ты ждать?\n\n"
    "🪶 Премиум-практики ждут тебя. Не откладывай путь.\n\n"
    "→ /subscribe",
    
    "🦅 **Орёл дарит свободу**\n\n"
    "Воин знает: каждый момент — подарок. Но большинство людей спят.\n\n"
    "Ты уже сделал первый шаг. Сделай второй.\n\n"
    "⚡ Глубокие практики доступны по подписке.\n\n"
    "→ /subscribe",
    
    "❤️ **Путь с сердцем**\n\n"
    "Карлос спрашивал: «Как узнать, что это мой путь?»\n"
    "Дон Хуан ответил: «Если на нём есть радость — это твой путь.»\n\n"
    "Есть ли радость в твоём ожидании?\n\n"
    "🌟 Открой полное руководство — подпишись сейчас.\n\n"
    "→ /subscribe",
    
    "🔥 **Останови внутренний диалог**\n\n"
    "Ты читаешь эти строки. Твой ум говорит: «Потом, потом...»\n\n"
    "Воин не говорит «потом». Воин действует **сейчас**.\n\n"
    "⏰ Подписка открывает новые горизонты. Начни сегодня.\n\n"
    "→ /subscribe",
    
    "🌄 **Второе внимание**\n\n"
    "Обычные люди видят мир один раз. Воин видит дважды.\n\n"
    "Первое внимание — это то, что ты уже знаешь.\n"
    "Второе внимание — это то, что скрыто за завесой.\n\n"
    "🗝️ Ключ ко второму вниманию — в премиум-разделе.\n\n"
    "→ /subscribe",
    
    "💀 **Разговор со смертью**\n\n"
    "«Я не умру сегодня» — говорит обычный человек.\n"
    "«Я могу умереть сегодня» — говорит воин.\n\n"
    "И поэтому он не тратит время зря.\n\n"
    "⚡ Твоё время — сейчас. Не жди.\n\n"
    "→ /subscribe"
]

REMINDERS_EN = [
    "🌑 **The Warrior Remembers Death**\n\n"
    "Death stands at your left shoulder. It can touch you at any moment.\n\n"
    "If you knew today was your last day — would you wait?\n\n"
    "🪶 Premium practices are waiting. Don't delay the path.\n\n"
    "→ /subscribe",
    
    "🦅 **The Eagle Grants Freedom**\n\n"
    "The warrior knows: every moment is a gift. But most people sleep.\n\n"
    "You've taken the first step. Take the second.\n\n"
    "⚡ Deep practices are available with subscription.\n\n"
    "→ /subscribe",
    
    "❤️ **The Path with Heart**\n\n"
    "Carlos asked: «How do I know this is my path?»\n"
    "Don Juan answered: «If there is joy on it — that is your path.»\n\n"
    "Is there joy in your waiting?\n\n"
    "🌟 Open the full guide — subscribe now.\n\n"
    "→ /subscribe"
]

def get_random_reminder(lang: str = "ru"):
    reminders = REMINDERS_RU if lang == "ru" else REMINDERS_EN
    return random.choice(reminders)

def should_send_reminder(last_reminder: str, days_interval: int = 5) -> bool:
    if not last_reminder:
        return True
    try:
        from datetime import datetime
        last_date = datetime.fromisoformat(last_reminder)
        now = datetime.now()
        days_passed = (now - last_date).days
        return days_passed >= days_interval
    except:
        return True
