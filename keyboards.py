from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Словари переводов кнопок
TRANSLATIONS = {
    "ru": {
        "stop_world": "🌑 Остановить мир",
        "death": "💀 Разговор со смертью",
        "heart": "❤️ Путь с сердцем",
        "dreams": "🦅 Видение снов",
        "intention": "⚡ Намерение",
        "mood_check": "😊 Как я себя чувствую?",
        "breathing": "🧘 Дыхание",
        "emergency": "🆘 Мне плохо",
        "good": "😊 Хорошо",
        "ok": "😐 Нормально",
        "bad": "😔 Плохо",
        "anxiety": "😰 Тревожно",
        "back": "🔙 Назад",
        "breathe_478": "🌊 4-7-8 (расслабление)",
        "breathe_equal": "🌬️ Равное дыхание",
        "breathe_fire": "🔥 Огненное дыхание",
        "phone": "📞 Телефон доверия",
        "quick_help": "🧘 Быстрая помощь",
        "menu": "В меню"
    },
    "en": {
        "stop_world": "🌑 Stop the World",
        "death": "💀 Talk with Death",
        "heart": "❤️ Path with Heart",
        "dreams": "🦅 Dreaming",
        "intention": "⚡ Intention",
        "mood_check": "😊 How do I feel?",
        "breathing": "🧘 Breathing",
        "emergency": "🆘 I feel bad",
        "good": "😊 Good",
        "ok": "😐 Okay",
        "bad": "😔 Bad",
        "anxiety": "😰 Anxious",
        "back": "🔙 Back",
        "breathe_478": "🌊 4-7-8 (relaxation)",
        "breathe_equal": "🌬️ Equal breathing",
        "breathe_fire": "🔥 Fire breathing",
        "phone": "📞 Helpline",
        "quick_help": "🧘 Quick help",
        "menu": "To menu"
    }
}

def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])

def get_main_menu_keyboard(lang: str = "ru"):
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["stop_world"], callback_data="session_stop_world")],
        [InlineKeyboardButton(text=t["death"], callback_data="session_death")],
        [InlineKeyboardButton(text=t["heart"], callback_data="session_heart")],
        [InlineKeyboardButton(text=t["dreams"], callback_data="session_dreams")],
        [InlineKeyboardButton(text=t["intention"], callback_data="session_intention")],
        [InlineKeyboardButton(text=t["mood_check"], callback_data="mood_check")],
        [InlineKeyboardButton(text=t["breathing"], callback_data="breathing")],
        [InlineKeyboardButton(text=t["emergency"], callback_data="emergency")]
    ])

def get_mood_keyboard(lang: str = "ru"):
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["good"], callback_data="mood_good")],
        [InlineKeyboardButton(text=t["ok"], callback_data="mood_ok")],
        [InlineKeyboardButton(text=t["bad"], callback_data="mood_bad")],
        [InlineKeyboardButton(text=t["anxiety"], callback_data="mood_anxiety")],
        [InlineKeyboardButton(text=t["back"], callback_data="main_menu")]
    ])

def get_breathing_keyboard(lang: str = "ru"):
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["breathe_478"], callback_data="breathe_478")],
        [InlineKeyboardButton(text=t["breathe_equal"], callback_data="breathe_equal")],
        [InlineKeyboardButton(text=t["breathe_fire"], callback_data="breathe_fire")],
        [InlineKeyboardButton(text=t["back"], callback_data="main_menu")]
    ])

def get_emergency_keyboard(lang: str = "ru"):
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["phone"], url="tel:88002000122")],
        [InlineKeyboardButton(text=t["quick_help"], callback_data="emergency_help")],
        [InlineKeyboardButton(text=t["menu"], callback_data="main_menu")]
    ])

def get_premium_sessions_keyboard(lang: str = "ru"):
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["dreams"], callback_data="session_dreams")],
        [InlineKeyboardButton(text=t["intention"], callback_data="session_intention")],
        [InlineKeyboardButton(text=t["back"], callback_data="main_menu")]
    ])
