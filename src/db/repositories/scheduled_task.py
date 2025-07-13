from sqlalchemy import select

from src.db.models import ScheduledTask
from src.db.repositories.base import BaseRepository


class ScheduledTaskRepository(BaseRepository[ScheduledTask]):
    def __init__(self, session):
        super().__init__(ScheduledTask, session)

    async def get_all_active(self) -> list[ScheduledTask]:
        """Возвращает все активные задачи."""
        stmt = select(self.model).where(self.model.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_phase_id(self, phase_id: int) -> list[ScheduledTask]:
        """
        Возвращает все задачи, привязанные к конкретной фазе.
        """
        stmt = select(self.model).where(self.model.phase_id == phase_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
