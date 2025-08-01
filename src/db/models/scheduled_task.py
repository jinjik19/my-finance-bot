from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    phase_id: Mapped[int] = mapped_column(ForeignKey("phases.id"))

    task_type: Mapped[str] = mapped_column(String)  # 'reminder'
    cron_day: Mapped[str]
    cron_hour: Mapped[int]

    reminder_text: Mapped[str | None]

    amount: Mapped[Decimal | None] = mapped_column(Numeric)
    from_envelope_id: Mapped[int | None] = mapped_column(ForeignKey("envelopes.id"))
    to_envelope_id: Mapped[int | None] = mapped_column(ForeignKey("envelopes.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
