from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.repo_holder import RepoHolder


class RepoMiddleware:
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            data["repo"] = RepoHolder(session)
            return await handler(event, data)
