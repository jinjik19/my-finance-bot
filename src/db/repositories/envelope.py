from sqlalchemy import select

from src.db.models import Envelope

from .base import BaseRepository


class EnvelopeRepository(BaseRepository[Envelope]):
    def __init__(self, session) -> None:
        super().__init__(Envelope, session)

    async def get_all_active(self, owner_id: int) -> list[Envelope]:
        """Возвращает все АКТИВНЫЕ конверты конкретного пользователя."""
        stmt = select(self.model).where(
            (self.model.owner_id == owner_id) | (self.model.owner_id.is_(None)),
            self.model.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_owner_id(self, owner_id: int) -> list[Envelope]:
        """Возвращает конверты конкретного пользователя."""
        stmt = select(self.model).where(
            (self.model.owner_id == owner_id),
            self.model.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Envelope | None:
        """Находит конверт по его точному имени."""
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
