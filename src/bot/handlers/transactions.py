import datetime as dt
from decimal import Decimal, InvalidOperation

import pytz
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import get_items_for_action_keyboard
from src.bot.states import AddTransaction, MakeTransfer, SetInitialBalance
from src.db.models.user import User
from src.db.repo_holder import RepoHolder

router = Router()


def get_aware_current_date(user: User) -> dt.date:
    """Получает текущую дату в таймзоне пользователя."""
    timezone = pytz.timezone(user.timezone)
    return dt.datetime.now(tz=timezone).date()


@router.message(F.text == "📈 Расход")
async def add_expense_start(message: Message, state: FSMContext):
    await state.update_data(trans_type="expense", _original_message_id=message.message_id)
    await state.set_state(AddTransaction.choosing_amount)
    await message.answer("Введите сумму расхода:")


@router.message(F.text == "💰 Доход")
async def add_income_start(message: Message, state: FSMContext):
    # Для дохода конверт определяется автоматически
    await state.update_data(trans_type="income", _original_message_id=message.message_id)
    await state.set_state(AddTransaction.choosing_amount)
    await message.answer("Введите сумму дохода:")


@router.message(AddTransaction.choosing_amount)
async def add_transaction_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()

    try:
        amount = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число.")
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    trans_type = data.get("trans_type")
    original_message_id = data.get("_original_message_id")

    all_categories = await repo.category.get_by_owner_id()
    filtered_categories = [cat for cat in all_categories if cat.type == trans_type]

    await state.set_state(AddTransaction.choosing_category)
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=original_message_id,
        text="Выберите категорию:",
        reply_markup=get_items_for_action_keyboard(filtered_categories, "select", "category"),
    )


@router.callback_query(AddTransaction.choosing_category, F.data.startswith("select:category:"))
async def add_transaction_category_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder, bot: Bot):
    category_id = int(callback.data.split(":")[-1])
    await state.update_data(category_id=category_id)

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    trans_type = data.get("trans_type")
    original_message_id = data.get("_original_message_id")

    # Для дохода конверт определяется автоматически
    if trans_type == "income":
        income_envelope = await repo.envelope.get_by_owner_id(user.id)

        if not income_envelope:
            await callback.message.edit_text(f"❌ Ошибка: доходный конверт для вас не найден. Обратитесь к администратору.")
            await state.clear()
            return

        await _finalize_add_transaction(callback, state, repo, user, income_envelope.id, bot, original_message_id)
        await callback.answer()
    else:
        envelopes = await repo.envelope.get_by_owner_id_or_null(user.id)
        await state.set_state(AddTransaction.choosing_envelope)
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=original_message_id,
            text="Выберите конверт:",
            reply_markup=get_items_for_action_keyboard(envelopes, "select", "envelope")
        )
        await callback.answer()


@router.callback_query(AddTransaction.choosing_envelope, F.data.startswith("select:envelope:"))
async def add_transaction_envelope_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder, bot: Bot):
    envelope_id = int(callback.data.split(":")[-1])
    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")
    await _finalize_add_transaction(callback, state, repo, user, envelope_id, bot, original_message_id)
    await callback.answer()


async def _finalize_add_transaction(
    callback: CallbackQuery,
    state: FSMContext,
    repo: RepoHolder,
    user: User,
    envelope_id: int,
    bot: Bot,
    original_message_id: int
):
    data = await state.get_data()
    trans_type = data.get("trans_type")
    amount = data.get("amount")
    category_id = data.get("category_id")

    envelope = await repo.envelope.get_by_id(envelope_id)

    if not envelope:
        await bot.edit_message_text("❌ Ошибка: конверт не найден.", chat_id=callback.message.chat.id, message_id=original_message_id)
        await state.clear()
        return

    if trans_type == "expense" and envelope.balance < amount:
        current_balance = f"Текущий баланс: {envelope.balance:.2f} ₽."
        await bot.edit_message_text(
            f"❌ Недостаточно средств на конверте «{envelope.name}».\n{current_balance}", 
            chat_id=callback.message.chat.id, 
            message_id=original_message_id,
            parse_mode="Markdown"
        )
        await state.clear()
        return

    transaction_date = get_aware_current_date(user)

    await repo.transaction.create(
        user_id=user.id,
        category_id=category_id,
        envelope_id=envelope_id,
        amount=amount,
        transaction_date=transaction_date,
    )

    new_balance = envelope.balance - amount if trans_type == "expense" else envelope.balance + amount
    await repo.envelope.update(envelope, balance=new_balance)

    await state.clear()
    await bot.edit_message_text(
        "✅ Успешно! Операция добавлена.", chat_id=callback.message.chat.id, message_id=original_message_id
    )


@router.message(F.text == "📋 Перевод")
async def make_transfer_start(message: Message, state: FSMContext):
    await state.set_state(MakeTransfer.choosing_amount)
    await state.update_data(_original_message_id=message.message_id)
    await message.answer("Введите сумму перевода:")


@router.message(MakeTransfer.choosing_amount)
async def make_transfer_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()

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
        data = await state.get_data()
        original_message_id = data.get("_original_message_id")
        await bot.edit_message_text(f"❌ Ни на одном из ваших конвертов нет достаточной суммы ({amount:.2f} ₽) для перевода.", chat_id=message.chat.id, message_id=original_message_id)
        await state.clear()
        return

    await state.set_state(MakeTransfer.choosing_envelope_from)
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")

    await bot.edit_message_text(
        "С какого конверта перевести?",
        chat_id=message.chat.id,
        message_id=original_message_id,
        reply_markup=get_items_for_action_keyboard(sufficient_balance_envelopes, "from", "envelope"),
    )


@router.callback_query(MakeTransfer.choosing_envelope_from, F.data.startswith("from:envelope:"))
async def make_transfer_from_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder, bot: Bot):
    envelope_from_id = int(callback.data.split(":")[-1])
    await state.update_data(envelope_from_id=envelope_from_id)

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    envelopes = await repo.envelope.get_by_owner_id(user.id)
    filtered_envelopes = [env for env in envelopes if env.id != envelope_from_id]

    data = await state.get_data()
    original_message_id = data.get("_original_message_id")

    await state.set_state(MakeTransfer.choosing_envelope_to)
    await bot.edit_message_text(
        "На какой конверт перевести?",
        chat_id=callback.message.chat.id,
        message_id=original_message_id,
        reply_markup=get_items_for_action_keyboard(filtered_envelopes, "to", "envelope"),
    )



@router.callback_query(MakeTransfer.choosing_envelope_to, F.data.startswith("to:envelope:"))
async def make_transfer_to_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder, bot: Bot):
    envelope_to_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    amount = data.get("amount")
    envelope_from_id = data.get("envelope_from_id")
    original_message_id = data.get("_original_message_id")

    env_from = await repo.envelope.get_by_id(envelope_from_id)
    env_to = await repo.envelope.get_by_id(envelope_to_id)

    if not env_from or not env_to:
        await bot.edit_message_text(
            "❌ Ошибка: один из конвертов не найден.", chat_id=callback.message.chat.id, message_id=original_message_id
        )
        await state.clear()
        return

    user = await repo.user.get_or_create(callback.from_user.id, callback.from_user.username)
    transfer_date = dt.datetime.now(tz=pytz.timezone(user.timezone))

    await repo.transfer.create(from_envelope_id=env_from.id, to_envelope_id=env_to.id, amount=amount, transfer_date=transfer_date)
    await repo.envelope.update(env_from, balance=env_from.balance - amount)
    await repo.envelope.update(env_to, balance=env_to.balance + amount)

    await state.clear()
    await bot.edit_message_text(
        f"✅ Перевод на сумму {amount:.2f} ₽ с «{env_from.name}» на «{env_to.name}» выполнен успешно!",
        chat_id=callback.message.chat.id,
        message_id=original_message_id,
    )


@router.message(F.text == "Внести остаток")
async def set_initial_balance_start(message: Message, state: FSMContext, repo: RepoHolder):
    await state.set_state(SetInitialBalance.choosing_envelope)
    await state.update_data(_original_message_id=message.message_id)
    user = await repo.user.get_or_create(message.from_user.id, message.from_user.username)

    await message.answer(
        "Выберите конверт для внесения остатка:",
        reply_markup=get_items_for_action_keyboard(
            await repo.envelope.get_by_owner_id_or_null(user.id),
            "set_balance",
            "envelope"
        )
    )


@router.callback_query(SetInitialBalance.choosing_envelope, F.data.startswith("set_balance:envelope:"))
async def set_initial_balance_envelope_chosen(callback: CallbackQuery, state: FSMContext):
    envelope_id = int(callback.data.split(":")[1])
    await state.update_data(envelope_id=envelope_id)
    await state.set_state(SetInitialBalance.waiting_for_amount)
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")
    await callback.message.edit_text("Введите новую сумму для баланса:", chat_id=callback.message.chat.id, message_id=original_message_id)
    await callback.answer()


@router.message(SetInitialBalance.waiting_for_amount)
async def set_initial_balance_amount_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    await message.delete()

    try:
        amount = Decimal(message.text.replace(",", "."))
    except InvalidOperation:
        await message.answer("Пожалуйста, введите корректное число.")
        return

    data = await state.get_data()
    envelope_id = data.get("envelope_id")
    original_message_id = data.get("_original_message_id")

    envelope = await repo.envelope.get_by_id(envelope_id)

    if not envelope:
        await bot.edit_message_text("❌ Ошибка: конверт не найден.", chat_id=message.chat.id, message_id=original_message_id)
    else:
        await repo.envelope.update(envelope, balance=amount)
        await bot.edit_message_text(f"✅ Баланс конверта «{envelope.name}» успешно установлен на {amount:.2f} ₽.", chat_id=message.chat.id, message_id=original_message_id)

    await state.clear()
