from sqlalchemy import (
    Boolean,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Category(Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
