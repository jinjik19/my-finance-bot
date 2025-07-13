import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Transfer(Base):
    __tablename__ = "transfers"
    from_envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    to_envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    amount: Mapped[float] = mapped_column(Numeric)
    transfer_date: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
