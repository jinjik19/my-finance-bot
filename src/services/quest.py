from decimal import Decimal

from src.db.repo_holder import RepoHolder


async def get_quest_report(user_id: int, repo: RepoHolder) -> str:
    """Готовит отчет о прогрессе по текущей главной цели."""
    system_state = await repo.state.get_by_id(1)

    if not system_state or not system_state.current_phase_id:
        return (
            "Финансовая фаза еще не установлена.\n\n"
            "Зайдите в `⚙️ Управление` -> `🗺️ Фазы`, чтобы выбрать текущую."
        )

    goal = await repo.goal.get_by_phase_id(system_state.current_phase_id)

    if not goal:
        return "Для текущей фазы не найдена главная цель. Проверьте настройки."

    current_amount = await repo.transfer.get_total_for_envelope(goal.linked_envelope_id)
    target_amount = goal.target_amount
    progress_percent = (Decimal(current_amount) / target_amount * 100) if target_amount > 0 else Decimal(0)

    filled_blocks = int(progress_percent / 10)
    empty_blocks = 10 - filled_blocks
    progress_bar = "🟩" * filled_blocks + "⬜️" * empty_blocks

    report_lines = [
        f"🔮 **Прогресс по квесту: «{goal.name}»**\n",
        f"{progress_bar} {progress_percent:.1f}%\n",
        f"Накоплено: `{current_amount:.2f} ₽`",
        f"Цель: `{target_amount:.2f} ₽`",
        f"Осталось: `{target_amount - Decimal(current_amount):.2f} ₽`",
    ]

    return "\n".join(report_lines)
