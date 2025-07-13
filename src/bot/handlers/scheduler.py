from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bot.keyboards import get_items_for_action_keyboard, get_task_type_keyboard
from src.bot.states import AddScheduledTask
from src.db.repo_holder import RepoHolder
from src.services.scheduler import reload_scheduler_jobs

router = Router()


@router.callback_query(F.data == "list_tasks")
async def list_scheduled_tasks(callback: CallbackQuery, repo: RepoHolder):
    system_state = await repo.state.get_by_id(1)

    if not system_state or not system_state.current_phase_id:
        await callback.answer("Сначала выберите активную фазу.", show_alert=True)
        return

    tasks = await repo.scheduled_task.get_by_phase_id(system_state.current_phase_id)

    await callback.message.edit_text("Задачи для текущей фазы:")

    if not tasks:
        await callback.message.answer("Активных задач для этой фазы нет.")
        return

    for task in tasks:
        if task.task_type == "reminder":
            details = f"Напомнить: '{task.reminder_text}'"
        else:
            from_env = await repo.envelope.get_by_id(task.from_envelope_id)
            to_env = await repo.envelope.get_by_id(task.to_envelope_id)
            details = f"Перевести {task.amount}₽ с «{from_env.name}» на «{to_env.name}»"

        text = f"Каждый {task.cron_day}-й день в {task.cron_hour}:00\n- {details}"

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✅ Включено" if task.is_active else "❌ Выключено", callback_data=f"toggle_task:{task.id}"
            )
        )
        await callback.message.answer(text, reply_markup=builder.as_markup())

    await callback.answer()


@router.callback_query(F.data.startswith("toggle_task:"))
async def toggle_task_status(callback: CallbackQuery, repo: RepoHolder, bot: Bot, session_pool: async_sessionmaker):
    task_id = int(callback.data.split(":")[1])
    task = await repo.scheduled_task.get_by_id(task_id)

    if not task:
        return await callback.answer("Задача не найдена.", show_alert=True)

    await repo.scheduled_task.update(task, is_active=not task.is_active)
    await reload_scheduler_jobs(bot, session_pool)
    await callback.answer("Статус задачи изменен. Расписание перезагружено.", show_alert=True)
    await list_scheduled_tasks(callback, repo)


@router.callback_query(F.data == "add_task")
async def add_task_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddScheduledTask.choosing_type)
    await callback.message.edit_text("Выберите тип новой задачи:", reply_markup=get_task_type_keyboard())


@router.callback_query(F.data.startswith("add_task_type:"))
async def add_task_type_chosen(callback: CallbackQuery, state: FSMContext):
    task_type = callback.data.split(":")[1]
    await state.update_data(task_type=task_type, _original_message_id=callback.message.message_id)
    await state.set_state(AddScheduledTask.choosing_day)
    await callback.message.edit_text("Введите день месяца для выполнения задачи (число от 1 до 28):")


@router.message(AddScheduledTask.choosing_day)
async def add_task_day_chosen(message: Message, state: FSMContext, bot: Bot):
    await message.delete()

    try:
        day = int(message.text)
        if not 1 <= day <= 28:
            raise ValueError
    except ValueError:
        await message.answer("Нужно ввести число от 1 до 28. Попробуйте снова.")
        return

    await state.update_data(day=day)
    await state.set_state(AddScheduledTask.choosing_hour)
    data = await state.get_data()
    await bot.edit_message_text(
        "Введите час выполнения задачи (число от 0 до 23):",
        chat_id=message.chat.id,
        message_id=data.get("_original_message_id"),
    )


@router.message(AddScheduledTask.choosing_hour)
async def add_task_hour_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()

    try:
        hour = int(message.text)

        if not 0 <= hour <= 23:
            raise ValueError

    except ValueError:
        await message.answer("Нужно ввести число от 0 до 23. Попробуйте снова.")
        return

    await state.update_data(hour=hour)
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")

    if data.get("task_type") == "reminder":
        await state.set_state(AddScheduledTask.waiting_for_text)
        await bot.edit_message_text(
            "Введите текст для напоминания:", chat_id=message.chat.id, message_id=original_message_id
        )
    else:  # auto_transfer
        await state.set_state(AddScheduledTask.waiting_for_amount)
        await bot.edit_message_text(
            "Введите сумму для авто-перевода:", chat_id=message.chat.id, message_id=original_message_id
        )


@router.message(AddScheduledTask.waiting_for_text)
async def add_task_reminder_text_chosen(
    message: Message, state: FSMContext, repo: RepoHolder, bot: Bot, session_pool: async_sessionmaker
):
    await message.delete()
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")
    system_state = await repo.state.get_by_id(1)

    await repo.scheduled_task.create(
        phase_id=system_state.current_phase_id,
        task_type="reminder",
        cron_day=str(data.get("day")),
        cron_hour=data.get("hour"),
        reminder_text=message.text,
    )
    await state.clear()
    await reload_scheduler_jobs(bot, session_pool)

    if original_message_id:
        await bot.edit_message_text(
            "✅ Новое напоминание успешно создано!", chat_id=message.chat.id, message_id=original_message_id
        )


@router.message(AddScheduledTask.waiting_for_amount)
async def add_task_transfer_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()

    try:
        amount = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число. Попробуйте снова.")
        return

    await state.update_data(amount=str(amount))  # Сохраняем как строку для JSON

    user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)
    envelopes = await repo.envelope.get_by_owner_id(user.id)

    await state.set_state(AddScheduledTask.choosing_envelope_from)
    data = await state.get_data()

    if data.get("_original_message_id"):
        await bot.edit_message_text(
            "С какого конверта перевести?",
            chat_id=message.chat.id,
            message_id=data.get("_original_message_id"),
            reply_markup=get_items_for_action_keyboard(envelopes, "select_task_from", "envelope"),
        )


@router.callback_query(AddScheduledTask.choosing_envelope_from, F.data.startswith("select_task_from:envelope:"))
async def add_task_from_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    from_id = int(callback.data.split(":")[-1])
    await state.update_data(from_envelope_id=from_id)

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelopes = await repo.envelope.get_by_owner_id(user.id)
    filtered_envelopes = [env for env in envelopes if env.id != from_id]

    await state.set_state(AddScheduledTask.choosing_envelope_to)
    await callback.message.edit_text(
        "На какой конверт перевести?",
        reply_markup=get_items_for_action_keyboard(filtered_envelopes, "select_task_to", "envelope"),
    )


@router.callback_query(AddScheduledTask.choosing_envelope_to, F.data.startswith("select_task_to:envelope:"))
async def add_task_to_chosen(
    callback: CallbackQuery, state: FSMContext, repo: RepoHolder, bot: Bot, session_pool: async_sessionmaker
):
    to_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    system_state = await repo.state.get_by_id(1)

    await repo.scheduled_task.create(
        phase_id=system_state.current_phase_id,
        task_type="auto_transfer",
        cron_day=str(data.get("day")),
        cron_hour=data.get("hour"),
        amount=Decimal(data.get("amount")),
        from_envelope_id=data.get("from_envelope_id"),
        to_envelope_id=to_id,
    )
    await state.clear()
    await reload_scheduler_jobs(bot, session_pool)
    await callback.message.edit_text("✅ Новая задача авто-перевода успешно создана!")
