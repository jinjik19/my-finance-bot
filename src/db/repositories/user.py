from sqlalchemy import select

from src.db.models import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session) -> None:
        super().__init__(User, session)

    async def get_or_create(self, telegram_id: int, username: str | None) -> User:
        """Находит пользователя по telegram_id или создает нового."""
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = await self.create(telegram_id=telegram_id, username=username)

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
