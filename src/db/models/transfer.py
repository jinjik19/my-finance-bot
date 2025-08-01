import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .envelope import Envelope


class Transfer(Base):
    __tablename__ = "transfers"
    from_envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    to_envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric)
    transfer_date: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    from_envelope: Mapped["Envelope"] = relationship(back_populates="transfers_from", foreign_keys=[from_envelope_id])
    to_envelope: Mapped["Envelope"] = relationship(back_populates="transfers_to", foreign_keys=[to_envelope_id])
