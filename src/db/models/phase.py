from decimal import Decimal

from sqlalchemy import Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Phase(Base):
    """Модель для Финансовой Фазы."""

    __tablename__ = "phases"
    name: Mapped[str] = mapped_column(unique=True)
    monthly_target: Mapped[Decimal] = mapped_column(Numeric)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
