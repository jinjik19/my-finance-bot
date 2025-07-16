import datetime as dt
from decimal import Decimal

from sqlalchemy import and_, func, select

from src.db.models import Envelope, Transfer
from src.db.repositories.base import BaseRepository


class TransferRepository(BaseRepository[Transfer]):
    def __init__(self, session):
        super().__init__(Transfer, session)

    async def get_savings_for_period(self, start_date: dt.datetime, end_date: dt.datetime) -> list[Transfer]:
        """Возвращает переводы в накопительные конверты за период."""
        stmt = (
            select(self.model)
            .join(Envelope, self.model.to_envelope_id == Envelope.id)
            .where(
                and_(
                    Envelope.is_savings == True,  # noqa: E712
                    self.model.transfer_date >= start_date,
                    self.model.transfer_date <= end_date,
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_for_envelope(self, to_envelope_id: int) -> float:
        """Считает общую сумму всех переводов на указанный конверт."""
        stmt = select(func.sum(self.model.amount)).where(self.model.to_envelope_id == to_envelope_id)
        result = await self.session.execute(stmt)
        total = result.scalar_one_or_none()

        return total or 0.0

    async def get_total_to_envelope(self, envelope_id: int) -> Decimal:
        """Считает сумму всех переводов НА конверт."""
        stmt = select(func.sum(self.model.amount)).where(self.model.to_envelope_id == envelope_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() or Decimal(0)

    async def get_total_from_envelope(self, envelope_id: int) -> Decimal:
        """Считает сумму всех переводов С конверта."""
        stmt = select(func.sum(self.model.amount)).where(self.model.from_envelope_id == envelope_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() or Decimal(0)
