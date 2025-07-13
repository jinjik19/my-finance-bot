import datetime as dt
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import get_items_for_action_keyboard
from src.bot.states import AddTransaction, MakeTransfer
from src.db.repo_holder import RepoHolder

router = Router()


@router.message((F.text == "📈 Расход") | (F.text == "💰 Доход"))
async def add_transaction_start(message: Message, state: FSMContext):
    trans_type = "expense" if message.text == "📈 Расход" else "income"
    await state.update_data(trans_type=trans_type)
    await state.set_state(AddTransaction.choosing_amount)
    await message.answer("Введите сумму:")


@router.message(AddTransaction.choosing_amount)
async def add_transaction_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder):
    try:
        amount = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число.")
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    trans_type = data.get("trans_type")

    all_categories = await repo.category.get_all_active()
    filtered_categories = [cat for cat in all_categories if cat.type == trans_type]

    await state.set_state(AddTransaction.choosing_category)
    await message.answer(
        "Выберите категорию:",
        reply_markup=get_items_for_action_keyboard(filtered_categories, "select", "category"),
    )


@router.callback_query(AddTransaction.choosing_category, F.data.startswith("select:category:"))
async def add_transaction_category_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    category_id = int(callback.data.split(":")[-1])
    await state.update_data(category_id=category_id)

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelopes = await repo.envelope.get_by_owner_id(user.id)

    await state.set_state(AddTransaction.choosing_envelope)
    await callback.message.edit_text(
        "Выберите конверт:", reply_markup=get_items_for_action_keyboard(envelopes, "select", "envelope")
    )


@router.callback_query(AddTransaction.choosing_envelope, F.data.startswith("select:envelope:"))
async def add_transaction_envelope_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    envelope_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    trans_type = data.get("trans_type")
    amount = data.get("amount")
    category_id = data.get("category_id")

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelope = await repo.envelope.get_by_id(envelope_id)

    if not envelope:
        await callback.message.edit_text("❌ Ошибка: конверт не найден.")
        await state.clear()
        return

    if trans_type == "expense" and envelope.balance < amount:
        current_balance = f"Текущий баланс: {envelope.balance:.2f} ₽."
        await callback.message.edit_text(
            f"❌ Недостаточно средств на конверте «{envelope.name}».\n{current_balance}", parse_mode="Markdown"
        )
        await state.clear()
        return

    await repo.transaction.create(
        user_id=user.id,
        category_id=category_id,
        envelope_id=envelope_id,
        amount=amount,
        transaction_date=dt.date.today(),
    )

    new_balance = envelope.balance - amount if trans_type == "expense" else envelope.balance + amount
    await repo.envelope.update(envelope, balance=new_balance)

    await state.clear()
    await callback.message.edit_text("✅ Успешно! Операция добавлена.")


@router.message(F.text == "📋 Перевод")
async def make_transfer_start(message: Message, state: FSMContext):
    await state.set_state(MakeTransfer.choosing_amount)
    await message.answer("Введите сумму перевода:")


@router.message(MakeTransfer.choosing_amount)
async def make_transfer_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder):
    try:
        amount = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число.")
        return

    await state.update_data(amount=amount)
    user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)
    envelopes = await repo.envelope.get_by_owner_id(user.id)
    sufficient_balance_envelopes = [env for env in envelopes if env.balance >= amount]

    if not sufficient_balance_envelopes:
        await message.answer(f"❌ Ни на одном из ваших конвертов нет достаточной суммы ({amount:.2f} ₽) для перевода.")
        await state.clear()
        return

    await state.set_state(MakeTransfer.choosing_envelope_from)
    await message.answer(
        "С какого конверта перевести?",
        # ИСПОЛЬЗУЕМ НОВУЮ КЛАВИАТУРУ
        reply_markup=get_items_for_action_keyboard(sufficient_balance_envelopes, "from", "envelope"),
    )


@router.callback_query(MakeTransfer.choosing_envelope_from, F.data.startswith("from:envelope:"))
async def make_transfer_from_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    envelope_from_id = int(callback.data.split(":")[-1])
    await state.update_data(envelope_from_id=envelope_from_id)

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelopes = await repo.envelope.get_by_owner_id(user.id)
    filtered_envelopes = [env for env in envelopes if env.id != envelope_from_id]

    await state.set_state(MakeTransfer.choosing_envelope_to)
    await callback.message.edit_text(
        "На какой конверт перевести?",
        reply_markup=get_items_for_action_keyboard(filtered_envelopes, "to", "envelope"),
    )


@router.callback_query(MakeTransfer.choosing_envelope_to, F.data.startswith("to:envelope:"))
async def make_transfer_to_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    envelope_to_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    amount = data.get("amount")
    envelope_from_id = data.get("envelope_from_id")

    env_from = await repo.envelope.get_by_id(envelope_from_id)
    env_to = await repo.envelope.get_by_id(envelope_to_id)

    if not env_from or not env_to:
        await callback.message.edit_text("❌ Ошибка: один из конвертов не найден.")
        await state.clear()
        return

    await repo.transfer.create(from_envelope_id=env_from.id, to_envelope_id=env_to.id, amount=amount)
    await repo.envelope.update(env_from, balance=env_from.balance - amount)
    await repo.envelope.update(env_to, balance=env_to.balance + amount)

    await state.clear()
    await callback.message.edit_text(
        f"✅ Перевод на сумму {amount:.2f} ₽ с «{env_from.name}» на «{env_to.name}» выполнен успешно!"
    )
