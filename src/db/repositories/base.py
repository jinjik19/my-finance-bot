from typing import Generic, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый класс для всех репозиториев, содержит CRUD операции."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, pk: int) -> ModelType | None:
        return await self.session.get(self.model, pk)

    async def get_all(self) -> list[ModelType]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def create(self, **data) -> ModelType:
        instance = self.model(**data)
        self.session.add(instance)

        await self.session.commit()
        await self.session.refresh(instance)

        return instance

    async def update(self, instance: ModelType, **data) -> ModelType:
        for key, value in data.items():
            setattr(instance, key, value)

        await self.session.commit()
        await self.session.refresh(instance)

        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.commit()
