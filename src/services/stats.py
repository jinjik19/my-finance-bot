import datetime as dt
from collections import defaultdict
from decimal import Decimal

import pytz

from src.core.settings import settings
from src.db.models.user import User
from src.db.repo_holder import RepoHolder

RU_MONTHS = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def _get_date_range(user_timezone: str) -> tuple[dt.date, dt.datetime]:
    """Возвращает начало и конец текущего месяца в таймзоне пользователя."""
    timezone = pytz.timezone(user_timezone)
    today = dt.datetime.now(tz=timezone).date()
    start_of_month = today.replace(day=1)
    end_of_today = dt.datetime.combine(today, dt.time.max)
    return start_of_month, end_of_today


async def _calculate_user_specific_balance(repo: RepoHolder, user: User, start_date: dt.date, end_date: dt.datetime) -> dict | None:
    """Рассчитывает остаток, новые доходы и текущий баланс для доходного конверта пользователя."""
    income_envelope = await repo.envelope.get_by_owner_id(user.id)

    if not income_envelope:
        return None

    # 1. Считаем все поступления (доходы/переводы) в доходный конверт за текущий месяц
    income_transactions_this_month = await repo.transaction.get_income_for_envelope_and_period(
        income_envelope.id, start_date, end_date
    )
    transfers_to_income_this_month = await repo.transfer.get_to_envelope_for_period(
        income_envelope.id, start_date, end_date
    )
    total_income_this_month = (
        sum(t.amount for t in income_transactions_this_month)
        + sum(t.amount for t in transfers_to_income_this_month)
    )

    # 2. Считаем все расходы (расходы/переводы) из доходного конверта за текущий месяц
    expense_transactions_this_month = await repo.transaction.get_expense_for_envelope_and_period(
        income_envelope.id, start_date, end_date
    )
    transfers_from_income_this_month = await repo.transfer.get_from_envelope_for_period(
        income_envelope.id, start_date, end_date
    )
    total_expense_this_month = (
        sum(t.amount for t in expense_transactions_this_month)
        + sum(t.amount for t in transfers_from_income_this_month)
    )

    # 3. Вычисляем баланс на начало месяца (Остаток с прошлого месяца)
    balance_at_start_of_month = income_envelope.balance - (total_income_this_month - total_expense_this_month)

    # Общий доступный фонд = Остаток с прошлого месяца + Доходы за текущий месяц
    total_available = balance_at_start_of_month + total_income_this_month

    return {
        "balance_at_start_of_month": balance_at_start_of_month,
        "total_income_this_month": total_income_this_month,
        "total_expense_this_month": total_expense_this_month,
        "total_available": total_available,
        "current_balance": income_envelope.balance,
        "envelope_name": income_envelope.name
    }


async def _calculate_total_stats(repo: RepoHolder, start_date: dt.date, end_date: dt.datetime) -> dict:
    """
    Рассчитывает общую статистику по всем пользователям.
    """
    user_ids = settings.allowed_telegram_ids
    users = [await repo.user.get_by_telegram_id(uid) for uid in user_ids]

    all_transactions = await repo.transaction.get_all_for_period(start_date, end_date)

    total_income = Decimal(0)
    total_expense = Decimal(0)
    expenses_by_user = defaultdict(Decimal)

    # Суммируем доходы/расходы из transactions
    for t in all_transactions:
        category = await repo.category.get_by_id(t.category_id)
        if category.type == "income":
            total_income += t.amount
        else:
            total_expense += t.amount
            expenses_by_user[t.user_id] += t.amount

    savings_transfers = await repo.transfer.get_all_savings_for_period(start_date, end_date)
    total_savings = sum(t.amount for t in savings_transfers)

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_savings": total_savings,
        "expenses_by_user": expenses_by_user,
        "users": users
    }


async def prepare_current_month_report(repo: RepoHolder, user: User) -> str:
    """Готовит расширенный текстовый отчет за текущий месяц."""
    start_of_month, end_of_today = _get_date_range(user.timezone)
    today = dt.datetime.now(tz=pytz.timezone(user.timezone)).date()
    user_balance_data = await _calculate_user_specific_balance(repo, user, start_of_month, end_of_today)
    total_stats = await _calculate_total_stats(repo, start_of_month, end_of_today)

    month_name = RU_MONTHS[start_of_month.month - 1]

    report_title = f"Отчет за {month_name} {today.year}"
    report_lines = [
        f"📊 **{report_title}**\n",
        f"---",
        f"**Ваши финансы ({user.username}):**",
    ]

    if user_balance_data:
        report_lines.extend([
            f"💰 **Новые доходы за месяц:** `{user_balance_data['total_income_this_month']:.2f} ₽`",
            f"🗂️ **Остаток с прошлого месяца:** `{user_balance_data['balance_at_start_of_month']:.2f} ₽`",
            f"💵 **Всего доступно:** `{user_balance_data['total_available']:.2f} ₽`",
            f"📈 **Расходы за месяц:** `{user_balance_data['total_expense_this_month']:.2f} ₽`",
            f"✅ **Текущий остаток на вашем конверте:** `{user_balance_data['current_balance']:.2f} ₽`\n",
        ])
    else:
        report_lines.append("❌ Ошибка: доходный конверт для вас не найден.\n")

    report_lines.extend([
        "---",
        "**Общая статистика:**",
        f"💰 Общий доход: `{total_stats['total_income']:.2f} ₽`",
        f"📈 Общие расходы: `{total_stats['total_expense']:.2f} ₽`",
        f"🎯 Отложено: `{total_stats['total_savings']:.2f} ₽`\n",
        "**Расходы по исполнителям:**",
    ])

    for u in total_stats['users']:
        report_lines.append(
            f" • {u.username or 'Пользователь'}: `{total_stats['expenses_by_user'].get(u.id, 0):.2f} ₽`"
        )


    return "\n".join(report_lines)
