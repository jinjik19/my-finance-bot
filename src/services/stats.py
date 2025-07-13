import datetime as dt
from collections import defaultdict
from decimal import Decimal

from src.core.settings import settings
from src.db.repo_holder import RepoHolder

RU_MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


async def prepare_current_month_report(repo: RepoHolder) -> str:
    """Готовит расширенный текстовый отчет за текущий месяц."""
    today = dt.date.today()
    start_of_month = today.replace(day=1)

    user1_id, user2_id = settings.allowed_telegram_ids
    user1 = await repo.user.get_by_telegram_id(user1_id)
    user2 = await repo.user.get_by_telegram_id(user2_id)

    if not user1 or not user2:
        return "Не удалось найти обоих пользователей в базе данных."

    user1_trans = await repo.transaction.get_for_period(user1.id, start_of_month, today)
    user2_trans = await repo.transaction.get_for_period(user2.id, start_of_month, today)
    all_transactions = user1_trans + user2_trans

    if not all_transactions:
        return "В этом месяце еще не было операций."

    total_income = Decimal(0)
    total_expense = Decimal(0)
    expenses_by_user = defaultdict(Decimal)

    for t in all_transactions:
        category = await repo.category.get_by_id(t.category_id)

        if category.type == "income":
            total_income += t.amount
        else:
            total_expense += t.amount
            expenses_by_user[t.user_id] += t.amount

    savings_transfers = await repo.transfer.get_savings_for_period(start_of_month, today)
    total_savings = sum(t.amount for t in savings_transfers)
    savings_rate = (total_savings / total_income * 100) if total_income > 0 else Decimal(0)

    net_profit = total_income - total_expense
    profit_emoji = "✅" if net_profit >= 0 else "❗️"

    month_name = RU_MONTHS[today.month - 1]
    report_title = f"Отчет за {month_name} {today.year}"

    report_lines = [
        f"📊 **{report_title}**\n",
        f"💰 Доходы: `{total_income:.2f} ₽`",
        f"📈 Расходы: `{total_expense:.2f} ₽`",
        f"{profit_emoji} Итог: `{net_profit:.2f} ₽`\n",
        f"🎯 **Норма сбережений: `{savings_rate:.1f}%`**",
        f"   (отложено `{total_savings:.2f} ₽` из `{total_income:.2f} ₽`)\n",
        "**Расходы по исполнителям:**",
        f" • {user1.username or 'Пользователь 1'}: `{expenses_by_user.get(user1.id, 0):.2f} ₽`",
        f" • {user2.username or 'Пользователь 2'}: `{expenses_by_user.get(user2.id, 0):.2f} ₽`",
    ]
    return "\n".join(report_lines)
