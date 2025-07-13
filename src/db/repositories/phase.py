from sqlalchemy import select

from src.db.models import Phase
from src.db.repositories.base import BaseRepository


class PhaseRepository(BaseRepository[Phase]):
    """Репозиторий для работы с финансовыми фазами."""

    def __init__(self, session):
        super().__init__(Phase, session)

    async def get_all_active(self) -> list[Phase]:
        """Возвращает все активные фазы."""
        stmt = select(self.model).where(self.model.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)

        return list(result.scalars().all())
