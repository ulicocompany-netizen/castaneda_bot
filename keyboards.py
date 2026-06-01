from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌑 Остановить мир", callback_data="session_stop_world")],
        [InlineKeyboardButton(text="💀 Разговор со смертью", callback_data="session_death")],
        [InlineKeyboardButton(text="❤️ Путь с сердцем", callback_data="session_heart")],
        [InlineKeyboardButton(text="🦅 Видение снов", callback_data="session_dreams")],
        [InlineKeyboardButton(text="⚡ Намерение", callback_data="session_intention")]
    ])

def get_premium_sessions_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Видение снов", callback_data="session_dreams")],
        [InlineKeyboardButton(text="⚡ Намерение", callback_data="session_intention")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
