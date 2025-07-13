from sqlalchemy.ext.asyncio import AsyncEngine

from src.db.models.base import Base


async def create_db_tables(engine: AsyncEngine):
    """Создает таблицы в БД на основе моделей SQLAlchemy."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
