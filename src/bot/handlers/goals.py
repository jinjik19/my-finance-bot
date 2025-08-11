from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import get_items_for_action_keyboard
from src.bot.states import AddGoal, EditGoal
from src.db.repo_holder import RepoHolder

router = Router()


@router.callback_query(F.data == "list_goals")
async def list_goals(callback: CallbackQuery, repo: RepoHolder):
    system_state = await repo.state.get_by_id(1)

    if not system_state or not system_state.current_phase_id:
        await callback.answer("Сначала нужно выбрать активную фазу в меню 'Управление' -> 'Фазы'.", show_alert=True)
        return

    goals = await repo.goal.get_all_by_phase_id(system_state.current_phase_id)

    if not goals:
        await callback.answer("Для текущей фазы нет активных целей.", show_alert=True)
        return

    response_text = "Цели для текущей фазы:\n"

    for goal in goals:
        envelope = await repo.envelope.get_by_id(goal.linked_envelope_id)
        phase = await repo.phase.get_by_id(goal.phase_id)

        if not envelope or not phase:
            continue

        progress = (envelope.balance / goal.target_amount * 100) if goal.target_amount > 0 else Decimal(0)

        response_text += (
            f"\n🎯 «{goal.name}» (Фаза: {phase.name})\n"
            f"   - Прогресс: {progress:.1f}%\n"
            f"   - Собрано: `{envelope.balance:.2f}` из `{goal.target_amount:.2f} ₽`"
        )

    await callback.message.edit_text(response_text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "add_goal")
async def add_goal_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddGoal.choosing_name)
    await state.update_data(_original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите название для новой цели:")
    await callback.answer()


@router.message(AddGoal.choosing_name)
async def add_goal_name_chosen(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(name=message.text)
    await state.set_state(AddGoal.choosing_target_amount)
    data = await state.get_data()
    if data.get("_original_message_id"):
        await bot.edit_message_text(
            "Отлично. Теперь введите целевую сумму (например, 150000):",
            chat_id=message.chat.id,
            message_id=data.get("_original_message_id"),
        )


@router.message(AddGoal.choosing_target_amount)
async def add_goal_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    try:
        target_amount = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число. Попробуйте еще раз.")
        return

    await state.update_data(target_amount=target_amount)

    user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)
    envelopes = await repo.envelope.get_all_active(user.id)
    await state.set_state(AddGoal.choosing_envelope)
    data = await state.get_data()

    if data.get("_original_message_id"):
        await bot.edit_message_text(
            "К какому накопительному конверту привязать эту цель?",
            chat_id=message.chat.id,
            message_id=data.get("_original_message_id"),
            reply_markup=get_items_for_action_keyboard(
                [e for e in envelopes if e.is_savings], "select_goal_env", "envelope"
            ),
        )


@router.callback_query(AddGoal.choosing_envelope, F.data.startswith("select_goal_env:envelope:"))
async def add_goal_envelope_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    envelope_id = int(callback.data.split(":")[-1])
    await state.update_data(linked_envelope_id=envelope_id)

    phases = await repo.phase.get_all_active()
    await state.set_state(AddGoal.choosing_phase)
    await callback.message.edit_text(
        "К какой финансовой фазе относится эта цель?",
        reply_markup=get_items_for_action_keyboard(phases, "select_goal_phase", "phase"),
    )


@router.callback_query(AddGoal.choosing_phase, F.data.startswith("select_goal_phase:phase:"))
async def add_goal_phase_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    phase_id = int(callback.data.split(":")[-1])
    data = await state.get_data()

    await repo.goal.create(
        name=data.get("name"),
        target_amount=data.get("target_amount"),
        linked_envelope_id=data.get("linked_envelope_id"),
        phase_id=phase_id,
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Цель «{data.get('name')}» успешно создана!")
    await callback.answer()


@router.callback_query(F.data == "edit_goal_menu")
async def edit_goal_menu(callback: CallbackQuery, repo: RepoHolder):
    goals = await repo.goal.get_all_active()
    await callback.message.edit_text(
        "Выберите цель для редактирования:",
        reply_markup=get_items_for_action_keyboard(goals, "edit", "goal"),
    )


@router.callback_query(F.data.startswith("edit:goal:"))
async def edit_goal_start(callback: CallbackQuery, state: FSMContext):
    goal_id = int(callback.data.split(":")[2])
    await state.set_state(EditGoal.waiting_for_new_name)  # Начнем с имени
    await state.update_data(goal_id=goal_id, _original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите новое название для цели:")
    await callback.answer()


@router.message(EditGoal.waiting_for_new_name)
async def edit_goal_name_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    data = await state.get_data()
    goal = await repo.goal.get_by_id(data.get("goal_id"))
    if goal:
        await repo.goal.update(goal, name=message.text)
        if data.get("_original_message_id"):
            await bot.edit_message_text(
                f"✅ Название цели изменено на «{message.text}».",
                chat_id=message.chat.id,
                message_id=data.get("_original_message_id"),
            )
    await state.clear()


@router.callback_query(F.data == "archive_goal_menu")
async def archive_goal_menu(callback: CallbackQuery, repo: RepoHolder):
    goals = await repo.goal.get_all_active()
    await callback.message.edit_text(
        "Выберите цель для архивации:",
        reply_markup=get_items_for_action_keyboard(goals, "archive", "goal"),
    )


@router.callback_query(F.data.startswith("archive:goal:"))
async def archive_goal(callback: CallbackQuery, repo: RepoHolder):
    goal_id = int(callback.data.split(":")[2])
    goal = await repo.goal.get_by_id(goal_id)

    if goal:
        await repo.goal.update(goal, status="archived")
        await callback.message.edit_text(f"✅ Цель «{goal.name}» архивирована.")

    await callback.answer()
