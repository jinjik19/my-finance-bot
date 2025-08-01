from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import get_edit_envelope_keyboard, get_items_for_action_keyboard
from src.bot.states import AddEnvelope, ArchiveTransfer, EditEnvelope
from src.db.repo_holder import RepoHolder

router = Router()


@router.callback_query(F.data == "list_envelopes")
async def list_envelopes(callback: CallbackQuery, repo: RepoHolder):
    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelopes = await repo.envelope.get_all_active(user.id)

    if not envelopes:
        await callback.answer("У вас пока нет активных конвертов.", show_alert=True)
        return

    response_text = "Ваши активные конверты:\n\n"

    for env in envelopes:
        savings_icon = "🎯" if env.is_savings else "🗂️"
        response_text += f"{savings_icon} «{env.name}»:  `{env.balance:.2f} ₽`\n"

    await callback.message.edit_text(response_text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "add_envelope")
async def add_envelope_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddEnvelope.choosing_name)
    await state.update_data(_original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите название для нового конверта:")
    await callback.answer()


@router.callback_query(F.data == "edit_envelope_menu")
async def edit_envelope_menu(callback: CallbackQuery, repo: RepoHolder):
    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelopes = await repo.envelope.get_all_active(user.id)
    await callback.message.edit_text(
        "Выберите конверт для редактирования:",
        reply_markup=get_items_for_action_keyboard(envelopes, "edit", "envelope"),
    )


@router.callback_query(F.data.startswith("edit:envelope:"))
async def edit_envelope_start(callback: CallbackQuery, repo: RepoHolder):
    """Показывает меню с опциями редактирования для выбранного конверта."""
    envelope_id = int(callback.data.split(":")[2])
    envelope = await repo.envelope.get_by_id(envelope_id)

    if not envelope:
        return await callback.answer("Конверт не найден", show_alert=True)

    await callback.message.edit_text(
        f"Редактирование конверта «{envelope.name}»:",
        reply_markup=get_edit_envelope_keyboard(envelope.id, envelope.is_savings),
    )


@router.callback_query(F.data.startswith("edit_envelope_name:"))
async def edit_envelope_name_start(callback: CallbackQuery, state: FSMContext):
    envelope_id = int(callback.data.split(":")[1])
    await state.set_state(EditEnvelope.waiting_for_new_name)
    await state.update_data(envelope_id=envelope_id, _original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите новое название для конверта:")


@router.message(EditEnvelope.waiting_for_new_name)
async def edit_envelope_name_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()
    data = await state.get_data()
    envelope = await repo.envelope.get_by_id(data.get("envelope_id"))

    if envelope:
        await repo.envelope.update(envelope, name=message.text)

        if data.get("_original_message_id"):
            await bot.edit_message_text(
                f"✅ Название конверта изменено на «{message.text}».",
                chat_id=message.chat.id,
                message_id=data.get("_original_message_id"),
            )

    await state.clear()


@router.callback_query(F.data.startswith("toggle_savings:envelope:"))
async def toggle_savings_envelope(callback: CallbackQuery, repo: RepoHolder):
    envelope_id = int(callback.data.split(":")[2])
    envelope = await repo.envelope.get_by_id(envelope_id)

    if envelope:
        new_status = not envelope.is_savings
        await repo.envelope.update(envelope, is_savings=new_status)
        status_text = "накопительным" if new_status else "обычным"
        await callback.answer(f"Конверт «{envelope.name}» теперь {status_text}.", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=get_edit_envelope_keyboard(envelope.id, new_status))
    else:
        await callback.answer("Конверт не найден.", show_alert=True)


@router.message(AddEnvelope.choosing_name)
async def add_envelope_name_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")

    user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)
    await repo.envelope.create(name=message.text, owner_id=user.id)

    await state.clear()

    if original_message_id:
        await bot.edit_message_text(
            text=f"✅ Конверт «{message.text}» создан.", chat_id=message.chat.id, message_id=original_message_id
        )


@router.callback_query(F.data.startswith("archive:envelope:"))
async def archive_envelope(callback: CallbackQuery, repo: RepoHolder, state: FSMContext):
    envelope_id = int(callback.data.split(":")[2])
    envelope = await repo.envelope.get_by_id(envelope_id)

    if not envelope:
        await callback.answer("Конверт не найден!", show_alert=True)
        return

    if envelope.balance > 0:
        await state.set_state(ArchiveTransfer.choosing_envelope_to)
        await state.update_data(from_envelope_id=envelope.id, amount=envelope.balance)

        user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
        all_envelopes = await repo.envelope.get_all_active(user.id)
        other_envelopes = [env for env in all_envelopes if env.id != envelope.id]

        await callback.message.edit_text(
            f"На конверте «{envelope.name}» осталось {envelope.balance:.2f} ₽. "
            "Нельзя архивировать непустой конверт.\n\n"
            "Пожалуйста, выберите конверт, куда перевести остаток:",
            reply_markup=get_items_for_action_keyboard(other_envelopes, "archive_transfer_to", "envelope"),
        )
    else:
        await repo.envelope.update(envelope, is_active=False)
        await callback.message.edit_text(f"✅ Конверт «{envelope.name}» успешно архивирован.")

    await callback.answer()


@router.callback_query(ArchiveTransfer.choosing_envelope_to, F.data.startswith("archive_transfer_to:envelope:"))
async def archive_transfer_to_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    """Завершает перевод остатка и архивирует конверт."""
    to_envelope_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    from_envelope_id = data.get("from_envelope_id")
    amount = data.get("amount")

    env_from = await repo.envelope.get_by_id(from_envelope_id)
    env_to = await repo.envelope.get_by_id(to_envelope_id)

    if not env_from or not env_to:
        await callback.message.edit_text("❌ Ошибка: один из конвертов не найден.")
        await state.clear()
        return

    await repo.transfer.create(from_envelope_id=env_from.id, to_envelope_id=env_to.id, amount=amount)
    await repo.envelope.update(env_from, balance=0, is_active=False)
    await repo.envelope.update(env_to, balance=env_to.balance + amount)

    await state.clear()
    await callback.message.edit_text(
        f"✅ Остаток {amount:.2f} ₽ переведен на «{env_to.name}».\n✅ Конверт «{env_from.name}» архивирован."
    )
    await callback.answer()


@router.message(F.text == "💰 Мой баланс")
async def show_my_balance(message: Message, repo: RepoHolder):
    user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)
    income_envelope = await repo.envelope.get_by_owner_id(user.id)

    if not income_envelope:
        await message.answer("❌ Ошибка: доходный конверт не найден.")
        return

    await message.answer(
        f"Текущий баланс на вашем доходном конверте «{income_envelope.name}»: `{income_envelope.balance:.2f} ₽`",
        parse_mode="Markdown"
    )
