import pytz
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards import get_main_menu_keyboard
from src.bot.states import CommonStates
from src.db.repo_holder import RepoHolder

router = Router()


@router.message(Command(commands=["start"]))
async def handle_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! Я готов к работе.", reply_markup=get_main_menu_keyboard()
    )


@router.message(F.text == "/set_timezone")
async def set_timezone_start(message: Message, state: FSMContext):
    await state.set_state(CommonStates.waiting_for_timezone)
    await message.answer(
        "Пожалуйста, отправьте мне название вашей таймзоны. "
        "Например: `Europe/Moscow` или `Asia/Tomsk`.\n"
        "Вы можете найти свою таймзону здесь: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
    )


@router.message(CommonStates.waiting_for_timezone)
async def set_timezone_finish(message: Message, state: FSMContext, repo: RepoHolder):
    try:
        pytz.timezone(message.text)
        user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)
        await repo.user.update(user, timezone=message.text)
        await message.answer(f"✅ Ваша таймзона успешно установлена на `{message.text}`.")
    except pytz.UnknownTimeZoneError:
        await message.answer(
            f"❌ Некорректное название таймзоны: `{message.text}`.\n"
            "Пожалуйста, попробуйте снова, используя формат `Region/City`."
        )
    finally:
        await state.clear()
