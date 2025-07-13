from decimal import Decimal
from sqlalchemy import func, or_, select

from src.db.models import Envelope
from src.db.models.category import Category

from .base import BaseRepository


class EnvelopeRepository(BaseRepository[Envelope]):
    def __init__(self, session) -> None:
        super().__init__(Envelope, session)

    async def get_by_owner_id(self, owner_id: int) -> list[Envelope]:
        """Возвращает все АКТИВНЫЕ конверты конкретного пользователя."""
        stmt = select(self.model).where(
            or_(self.model.owner_id == owner_id, self.model.owner_id == None),
            self.model.is_active == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
