import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .envelope import Envelope
    from .transaction import Transaction


class User(Base):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None]
    timezone: Mapped[str] = mapped_column(String, default="Asia/Tomsk")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    envelopes: Mapped[list["Envelope"]] = relationship(back_populates="owner")
