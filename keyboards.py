from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬 English", callback_data="lang_en")]
    ])

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Остановить мир", callback_data="session_stop_world")],
        [InlineKeyboardButton(text=" Разговор со смертью", callback_data="session_death")],
        [InlineKeyboardButton(text="❤️ Путь с сердцем", callback_data="session_heart")],
        [InlineKeyboardButton(text=" Видение снов", callback_data="session_dreams")],
        [InlineKeyboardButton(text=" Намерение", callback_data="session_intention")],
        [InlineKeyboardButton(text="😊 Как я себя чувствую?", callback_data="mood_check")],
        [InlineKeyboardButton(text=" Дыхание", callback_data="breathing")],
        [InlineKeyboardButton(text="🆘 Мне плохо", callback_data="emergency")]
    ])

def get_mood_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😊 Хорошо", callback_data="mood_good")],
        [InlineKeyboardButton(text="😐 Нормально", callback_data="mood_ok")],
        [InlineKeyboardButton(text="😔 Плохо", callback_data="mood_bad")],
        [InlineKeyboardButton(text="😰 Тревожно", callback_data="mood_anxiety")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def get_breathing_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌊 4-7-8 (расслабление)", callback_data="breathe_478")],
        [InlineKeyboardButton(text="🌬️ Равное дыхание", callback_data="breathe_equal")],
        [InlineKeyboardButton(text="🔥 Огненное дыхание", callback_data="breathe_fire")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def get_emergency_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Телефон доверия", url="tel:88002000122")],
        [InlineKeyboardButton(text="🧘 Быстрая помощь", callback_data="emergency_help")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
    ])

def get_premium_sessions_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Видение снов", callback_data="session_dreams")],
        [InlineKeyboardButton(text="⚡ Намерение", callback_data="session_intention")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
