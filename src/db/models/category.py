from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .transaction import Transaction


class Category(Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")
