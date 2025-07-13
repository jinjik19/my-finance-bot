from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards import (
    get_categories_manage_menu,
    get_envelopes_manage_menu,
    get_phases_manage_menu,
)
from src.bot.keyboards.inline import get_goals_manage_menu, get_scheduler_manage_menu

router = Router()


def get_main_manage_keyboard():
    """Создает основное меню управления с кнопкой 'Фазы'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗂️ Конверты", callback_data="manage_envelopes"),
        InlineKeyboardButton(text="🏷️ Категории", callback_data="manage_categories"),
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Цели", callback_data="manage_goals"),
        InlineKeyboardButton(text="🗺️ Фазы", callback_data="manage_phases"),
    )
    builder.row(InlineKeyboardButton(text="🔔 Напоминания", callback_data="manage_scheduler"))

    return builder.as_markup()


@router.message(F.text == "⚙️ Управление")
async def main_manage_menu(message: Message):
    await message.answer("Выберите, чем хотите управлять:", reply_markup=get_main_manage_keyboard())


@router.callback_query(F.data == "back_to_main_manage")
async def back_to_main_manage_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите, чем хотите управлять:", reply_markup=get_main_manage_keyboard())


@router.callback_query(F.data == "manage_envelopes")
async def to_envelopes_menu(callback: CallbackQuery):
    await callback.message.edit_text("Меню управления конвертами:", reply_markup=get_envelopes_manage_menu())


@router.callback_query(F.data == "manage_categories")
async def to_categories_menu(callback: CallbackQuery):
    await callback.message.edit_text("Меню управления категориями:", reply_markup=get_categories_manage_menu())


@router.callback_query(F.data == "manage_goals")
async def to_goals_menu(callback: CallbackQuery):
    await callback.message.edit_text("Меню управления целями:", reply_markup=get_goals_manage_menu())


@router.callback_query(F.data == "manage_phases")
async def to_phases_menu(callback: CallbackQuery):
    await callback.message.edit_text("Меню управления Финансовыми Фазами:", reply_markup=get_phases_manage_menu())


@router.callback_query(F.data == "manage_scheduler")
async def to_scheduler_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Меню управления напоминаниями и задачами:", reply_markup=get_scheduler_manage_menu()
    )
