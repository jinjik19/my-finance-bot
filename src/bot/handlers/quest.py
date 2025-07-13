from aiogram import F, Router
from aiogram.types import Message

from src.db.repo_holder import RepoHolder
from src.services.quest import get_quest_report

router = Router()


@router.message(F.text == "🔮 Мой квест")
async def show_quest_progress(message: Message, repo: RepoHolder):
    """
    Показывает отчет о прогрессе по главной цели текущей
    финансовой фазы пользователя.
    """
    report = await get_quest_report(message.from_user.id, repo)
    await message.answer(report, parse_mode="Markdown")
