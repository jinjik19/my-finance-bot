from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.settings import settings
from src.db.repo_holder import RepoHolder
from src.services.stats import prepare_current_month_report

router = Router()


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message, repo: RepoHolder):
    """
    Присылает пользователю отчет за текущий месяц и кнопку
    для перехода в Metabase.
    """
    # Вызываем сервис, который выполнит все вычисления
    report_text = await prepare_current_month_report(repo)

    # Создаем клавиатуру с кнопкой для Metabase, если он настроен
    builder = InlineKeyboardBuilder()
    if settings.metabase_url and "localhost" not in settings.metabase_url:
        builder.row(InlineKeyboardButton(text="Открыть дэшборд", url=settings.metabase_url))

    await message.answer(
        report_text, parse_mode="Markdown", reply_markup=builder.as_markup(), disable_web_page_preview=True
    )
