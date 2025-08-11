from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bot.keyboards import get_edit_phase_keyboard, get_items_for_action_keyboard, get_phases_keyboard
from src.bot.states import AddPhase, EditPhase
from src.db.repo_holder import RepoHolder
from src.services.scheduler import reload_scheduler_jobs

router = Router()


@router.callback_query(F.data == "list_phases")
async def list_phases(callback: CallbackQuery, repo: RepoHolder):
    system_state = await repo.state.get_by_id(1)
    all_phases = await repo.phase.get_all_active()
    await callback.message.edit_text(
        "Выберите вашу текущую финансовую фазу (отмечена ✅):",
        reply_markup=get_phases_keyboard(all_phases, system_state.current_phase_id if system_state else None),
    )


@router.callback_query(F.data.startswith("set_phase:"))
async def set_user_phase(callback: CallbackQuery, repo: RepoHolder, bot: Bot, session_pool: async_sessionmaker):
    phase_id = int(callback.data.split(":")[1])
    system_state = await repo.state.get_by_id(1)

    if not system_state:
        await repo.state.create(id=1, current_phase_id=phase_id)
        await reload_scheduler_jobs(bot, session_pool)
        await callback.answer("✅ Начальная фаза установлена. Расписание загружено.", show_alert=True)
        await list_phases(callback, repo)
        return

    old_phase_id = system_state.current_phase_id

    if old_phase_id == phase_id:
        await callback.answer("Эта фаза уже является активной.")
        return

    old_goal = await repo.goal.get_by_phase_id(old_phase_id)
    new_goal = await repo.goal.get_by_phase_id(phase_id)

    # Проверяем, что у обеих фаз есть цели и они привязаны к одному конверту
    if old_goal and new_goal and old_goal.linked_envelope_id == new_goal.linked_envelope_id:
        envelope = await repo.envelope.get_by_id(old_goal.linked_envelope_id)

        # Считаем остаток
        surplus = envelope.balance - old_goal.target_amount

        if surplus < 0:
            surplus = Decimal(0) # Не переносим долг

        # 1. Архивируем старую цель
        await repo.goal.update(old_goal, status='archived')

        # 2. Создаем "виртуальный" перевод остатка
        # Мы не меняем баланс, а создаем запись о переводе, чтобы учесть ее в прогрессе новой цели
        if surplus > 0:
            # Создаем фиктивный "Системный" конверт для отслеживания таких переносов
            system_envelope = await repo.envelope.get_by_name("System")

            if not system_envelope:
                system_envelope = await repo.envelope.create(name="System", is_active=False)

            await repo.transfer.create(
                from_envelope_id=system_envelope.id,
                to_envelope_id=new_goal.linked_envelope_id,
                amount=surplus
            )
            await callback.message.answer(
                f"🎉 Фаза «{old_goal.name}» завершена!\n"
                f"Остаток `{surplus:.2f} ₽` перенесен на новую цель «{new_goal.name}»."
            )

    # 3. Устанавливаем новую фазу
    await repo.state.update(system_state, current_phase_id=phase_id)

    # 4. Перезагружаем расписание
    await reload_scheduler_jobs(bot, session_pool)

    new_phase = await repo.phase.get_by_id(phase_id)
    await callback.answer(f"✅ Установлена фаза: {new_phase.name}. Расписание обновлено.", show_alert=True)
    await list_phases(callback, repo)


@router.callback_query(F.data == "add_phase")
async def add_phase_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddPhase.choosing_name)
    await state.update_data(_original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите название для новой фазы:")
    await callback.answer()


@router.message(AddPhase.choosing_name)
async def add_phase_name_chosen(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(name=message.text)
    await state.set_state(AddPhase.choosing_monthly_target)
    data = await state.get_data()

    if data.get("_original_message_id"):
        await bot.edit_message_text(
            "Отлично! Теперь введите ежемесячную цель по накоплениям для этой фазы (например, 75000):",
            chat_id=message.chat.id,
            message_id=data.get("_original_message_id"),
        )


@router.message(AddPhase.choosing_monthly_target)
async def add_phase_target_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    try:
        monthly_target = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число. Попробуйте еще раз.")
        return

    data = await state.get_data()
    await repo.phase.create(name=data.get("name"), monthly_target=monthly_target)
    await state.clear()

    if data.get("_original_message_id"):
        await bot.edit_message_text(
            f"✅ Новая фаза «{data.get('name')}» успешно создана!",
            chat_id=message.chat.id,
            message_id=data.get("_original_message_id"),
        )


@router.callback_query(F.data == "edit_phase_menu")
async def edit_phase_menu(callback: CallbackQuery, repo: RepoHolder):
    phases = await repo.phase.get_all_active()
    await callback.message.edit_text(
        "Выберите фазу для редактирования:",
        reply_markup=get_items_for_action_keyboard(phases, "edit", "phase"),
    )


@router.callback_query(F.data.startswith("edit:phase:"))
async def edit_phase_start(callback: CallbackQuery):
    phase_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(
        "Что именно вы хотите изменить в этой фазе?", reply_markup=get_edit_phase_keyboard(phase_id)
    )


@router.callback_query(F.data.startswith("edit_phase_name:"))
async def edit_phase_name_start(callback: CallbackQuery, state: FSMContext):
    phase_id = int(callback.data.split(":")[1])
    await state.set_state(EditPhase.waiting_for_new_name)
    await state.update_data(phase_id=phase_id, _original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите новое название фазы:")


@router.message(EditPhase.waiting_for_new_name)
async def edit_phase_name_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):

    data = await state.get_data()
    phase = await repo.phase.get_by_id(data.get("phase_id"))

    if phase:
        await repo.phase.update(phase, name=message.text)

        if data.get("_original_message_id"):
            await bot.edit_message_text(
                f"✅ Название фазы изменено на «{message.text}».",
                chat_id=message.chat.id,
                message_id=data.get("_original_message_id"),
            )

    await state.clear()


@router.callback_query(F.data.startswith("edit_phase_target:"))
async def edit_phase_target_start(callback: CallbackQuery, state: FSMContext):
    phase_id = int(callback.data.split(":")[1])
    await state.set_state(EditPhase.waiting_for_new_target)
    await state.update_data(phase_id=phase_id, _original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите новую месячную цель накоплений:")


@router.message(EditPhase.waiting_for_new_target)
async def edit_phase_target_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    try:
        monthly_target = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число. Попробуйте еще раз.")
        return

    data = await state.get_data()
    phase = await repo.phase.get_by_id(data.get("phase_id"))

    if phase:
        await repo.phase.update(phase, monthly_target=monthly_target)

        if data.get("_original_message_id"):
            await bot.edit_message_text(
                f"✅ Месячная цель для фазы «{phase.name}» изменена на {monthly_target:.2f} ₽.",
                chat_id=message.chat.id,
                message_id=data.get("_original_message_id"),
            )
    await state.clear()


@router.callback_query(F.data == "archive_phase_menu")
async def archive_phase_menu(callback: CallbackQuery, repo: RepoHolder):
    phases = await repo.phase.get_all_active()
    await callback.message.edit_text(
        "Выберите фазу для архивации:",
        reply_markup=get_items_for_action_keyboard(phases, "archive", "phase"),
    )


@router.callback_query(F.data.startswith("archive:phase:"))
async def archive_phase(callback: CallbackQuery, repo: RepoHolder):
    phase_id = int(callback.data.split(":")[2])
    phase = await repo.phase.get_by_id(phase_id)

    if not phase:
        return await callback.answer("Фаза не найдена", show_alert=True)

    system_state = await repo.state.get_by_id(1)

    if system_state and system_state.current_phase_id == phase.id:
        await callback.answer("Нельзя архивировать текущую активную фазу!", show_alert=True)
        return

    await repo.phase.update(phase, is_active=False)
    await callback.message.edit_text(f"✅ Фаза «{phase.name}» архивирована.")
    await callback.answer()
