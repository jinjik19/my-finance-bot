import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None]
    timezone: Mapped[str] = mapped_column(String, default="Asia/Tomsk")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
