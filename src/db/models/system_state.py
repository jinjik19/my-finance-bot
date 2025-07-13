from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SystemState(Base):
    """Таблица для хранения глобального состояния. Будет иметь всего одну запись."""
    __tablename__ = "system_state"
    current_phase_id: Mapped[int | None] = mapped_column(ForeignKey("phases.id"))
