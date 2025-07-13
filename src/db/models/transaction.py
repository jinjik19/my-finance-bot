import datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Transaction(Base):
    __tablename__ = "transactions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    envelope_id: Mapped[int] = mapped_column(ForeignKey("envelopes.id"))
    amount: Mapped[float] = mapped_column(Numeric)
    transaction_date: Mapped[datetime.date] = mapped_column(Date)
    comment: Mapped[str | None]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
