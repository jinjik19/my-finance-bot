from src.db.models import SystemState
from src.db.repositories.base import BaseRepository


class SystemStateRepository(BaseRepository[SystemState]):
    def __init__(self, session):
        super().__init__(SystemState, session)
