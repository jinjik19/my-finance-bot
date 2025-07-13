from sqlalchemy import select

from src.db.models import Category

from .base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session) -> None:
        super().__init__(Category, session)

    async def get_all_active(self) -> list[Category]:
        """Возвращает все активные категории."""
        stmt = select(self.model).where(self.model.is_active)
        result = await self.session.execute(stmt)

        return list(result.scalars().all())
