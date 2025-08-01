from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает главное меню с основными разделами."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📈 Расход"),
        KeyboardButton(text="💰 Доход"),
    )
    builder.row(
        KeyboardButton(text="📋 Перевод"),
        KeyboardButton(text="📊 Статистика"),
    )
    builder.row(
        KeyboardButton(text="💰 Мой баланс"),
        KeyboardButton(text="🔮 Мой квест"),
        KeyboardButton(text="⚙️ Управление"),
    )

    return builder.as_markup(resize_keyboard=True)
