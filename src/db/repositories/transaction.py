import datetime as dt
from decimal import Decimal

from sqlalchemy import and_, func, select

from src.db.models import Transaction
from src.db.models.category import Category
from src.db.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session):
        super().__init__(Transaction, session)

    async def get_for_period(
        self, user_id: int, start_date: dt.date, end_date: dt.date
    ) -> list[Transaction]:
        """Возвращает транзакции пользователя за указанный период."""
        stmt = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.transaction_date >= start_date,
                self.model.transaction_date <= end_date,
            )
        )
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def get_total_for_envelope_by_type(self, envelope_id: int, trans_type: str) -> Decimal:
        """Считает сумму транзакций для конверта по типу (доход/расход)."""
        stmt = select(func.sum(self.model.amount)).join(
            Category, self.model.category_id == Category.id
        ).where(
            self.model.envelope_id == envelope_id,
            Category.type == trans_type
        )
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() or Decimal(0)
