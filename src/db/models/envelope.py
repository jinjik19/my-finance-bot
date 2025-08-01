from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .transaction import Transaction
    from .transfer import Transfer
    from .user import User


class Envelope(Base):
    __tablename__ = "envelopes"
    name: Mapped[str] = mapped_column(String)
    balance: Mapped[Decimal] = mapped_column(Numeric, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_savings: Mapped[bool] = mapped_column(Boolean, default=False)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="envelope")
    transfers_from: Mapped[list["Transfer"]] = relationship(
        back_populates="from_envelope", foreign_keys="Transfer.from_envelope_id"
    )
    transfers_to: Mapped[list["Transfer"]] = relationship(
        back_populates="to_envelope", foreign_keys="Transfer.to_envelope_id"
    )
    owner: Mapped["User"] = relationship(back_populates="envelopes")
