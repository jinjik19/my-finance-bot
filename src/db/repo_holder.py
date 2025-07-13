from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories import (
    CategoryRepository,
    EnvelopeRepository,
    GoalRepository,
    PhaseRepository,
    ScheduledTaskRepository,
    SystemStateRepository,
    TransactionRepository,
    TransferRepository,
    UserRepository,
)


class RepoHolder:
    """Этот класс содержит все репозитории для удобной передачи в хендлеры."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user = UserRepository(session)
        self.envelope = EnvelopeRepository(session)
        self.category = CategoryRepository(session)
        self.transaction = TransactionRepository(session)
        self.transfer = TransferRepository(session)
        self.phase = PhaseRepository(session)
        self.goal = GoalRepository(session)
        self.state = SystemStateRepository(session)
        self.scheduled_task = ScheduledTaskRepository(session)
