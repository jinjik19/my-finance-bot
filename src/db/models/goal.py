from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Goal(Base):
    __tablename__ = "goals"
    name: Mapped[str] = mapped_column(String)
    target_amount: Mapped[float] = mapped_column(Numeric)
    linked_envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    status: Mapped[str] = mapped_column(String, default="active") # active, archived
    phase_id: Mapped[int] = mapped_column(ForeignKey("phases.id"))
