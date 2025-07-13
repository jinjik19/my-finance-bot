from sqlalchemy import select

from src.db.models import Goal

from .base import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    def __init__(self, session) -> None:
        super().__init__(Goal, session)

    async def get_all_active(self) -> list[Goal]:
        """Возвращает все активные цели."""
        stmt = select(self.model).where(self.model.status == "active")
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def get_by_phase_id(self, phase_id: int) -> Goal | None:
        """Находит активную цель, привязанную к конкретной фазе."""
        stmt = select(self.model).where(self.model.phase_id == phase_id, self.model.status == "active")
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_all_by_phase_id(self, phase_id: int) -> list[Goal]:
        """
        Находит ВСЕ активные цели, привязанные к фазе (для списков).
        """
        stmt = select(self.model).where(
            self.model.phase_id == phase_id,
            self.model.status == "active"
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
