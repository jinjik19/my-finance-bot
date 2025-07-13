from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Envelope(Base):
    __tablename__ = "envelopes"
    name: Mapped[str] = mapped_column(String)
    balance: Mapped[float] = mapped_column(Numeric, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_savings: Mapped[bool] = mapped_column(Boolean, default=False)
