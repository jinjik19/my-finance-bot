import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .category import Category
    from .envelope import Envelope
    from .user import User


class Transaction(Base):
    __tablename__ = "transactions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric)
    transaction_date: Mapped[datetime.date] = mapped_column(Date)
    comment: Mapped[str | None]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["Category"] = relationship(back_populates="transactions")
    user: Mapped["User"] = relationship(back_populates="transactions")
    envelope: Mapped["Envelope"] = relationship(back_populates="transactions")
