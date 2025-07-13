from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.keyboards import get_main_menu_keyboard

router = Router()

@router.message(Command(commands=["start"]))
async def handle_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! Я готов к работе.",
        reply_markup=get_main_menu_keyboard()
    )
