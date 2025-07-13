import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.bot.handlers import (
    categories,
    common,
    envelopes,
    goals,
    manage,
    phases,
    quest,
    scheduler,
    stats,
    transactions,
)
from src.bot.middlewares.auth import AuthMiddleware
from src.bot.middlewares.repo import RepoMiddleware
from src.core.settings import settings
from src.db.utils import create_db_tables
from src.services.scheduler import reload_scheduler_jobs, start_scheduler

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    engine = create_async_engine(str(settings.database_url), echo=True)
    session_pool = async_sessionmaker(engine, expire_on_commit=False)

    await create_db_tables(engine=engine)
    storage = MemoryStorage()

    # Инициализация бота и диспетчера
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=storage, session_pool=session_pool)

    # Подключаем middleware для аутентификации
    dp.update.middleware(AuthMiddleware())
    dp.update.middleware(RepoMiddleware(session_pool=session_pool))

    # Подключаем роутеры
    dp.include_router(common.router)
    dp.include_router(manage.router)
    dp.include_router(quest.router)
    dp.include_router(goals.router)
    dp.include_router(phases.router)
    dp.include_router(transactions.router)
    dp.include_router(stats.router)
    dp.include_router(envelopes.router)
    dp.include_router(categories.router)
    dp.include_router(scheduler.router)

    start_scheduler()
    await reload_scheduler_jobs(bot, session_pool)

    # Запуск бота
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
