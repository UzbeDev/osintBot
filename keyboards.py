from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Target Username (/u)", callback_data="opt_username")],
            [InlineKeyboardButton(text="📧 Target Email (/g)", callback_data="opt_email")],
            [InlineKeyboardButton(text="📱 Target Phone (/p)", callback_data="opt_phone")],
            [InlineKeyboardButton(text="⚡ Funstat Telegram (/f)", callback_data="opt_funstat")],
        ]
    )
