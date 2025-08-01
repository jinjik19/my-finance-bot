import datetime as dt
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from src.db.models import Transaction
from src.db.models.category import Category
from src.db.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session):
        super().__init__(Transaction, session)

    async def get_by_user_id(self, user_id: int) -> list[Transaction]:
        """Возвращает все транзакции конкретного пользователя."""
        stmt = select(self.model).where(self.model.user_id == user_id).options(
            joinedload(self.model.category)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_period(self, user_id: int, start_date: dt.datetime, end_date: dt.datetime) -> list[Transaction]:
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

    async def get_all_for_period(self, start_date: dt.date, end_date: dt.datetime) -> list[Transaction]:
        """Возвращает все транзакции за указанный период, без фильтра по пользователю."""
        stmt = select(self.model).where(
            and_(
                self.model.transaction_date >= start_date,
                self.model.transaction_date < end_date,
            )
        ).options(joinedload(self.model.category))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_for_envelope_by_type(self, envelope_id: int, trans_type: str) -> Decimal:
        """Считает сумму транзакций для конверта по типу (доход/расход)."""
        stmt = (
            select(func.sum(self.model.amount))
            .join(Category, self.model.category_id == Category.id)
            .where(self.model.envelope_id == envelope_id, Category.type == trans_type)
        )
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() or Decimal(0)

    async def get_income_for_envelope_and_period(
        self,
        envelope_id: int,
        start_date: dt.date,
        end_date: dt.datetime,
    ) -> list[Transaction]:
        """Возвращает доходы для конкретного конверта за период."""
        stmt = select(self.model).join(Category).where(
            and_(
                self.model.envelope_id == envelope_id,
                self.model.transaction_date >= start_date,
                self.model.transaction_date < end_date,
                Category.type == 'income',
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expense_for_envelope_and_period(
        self,
        envelope_id: int,
        start_date: dt.date,
        end_date: dt.datetime,
    ) -> list[Transaction]:
        """Возвращает расходы для конкретного конверта за период."""
        stmt = select(self.model).join(Category).where(
            and_(
                self.model.envelope_id == envelope_id,
                self.model.transaction_date >= start_date,
                self.model.transaction_date < end_date,
                Category.type == 'expense'
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_expenses_for_period_and_envelopes(
        self,
        user_id: int,
        envelope_ids: list[int],
        start_date: dt.date,
        end_date: dt.datetime,
    ) -> list[Transaction]:
        """Возвращает все расходы пользователя за период по списку конвертов."""
        stmt = select(self.model).join(Category).where(
            and_(
                self.model.user_id == user_id,
                self.model.envelope_id.in_(envelope_ids),
                self.model.transaction_date >= start_date,
                self.model.transaction_date < end_date,
                Category.type == 'expense'
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
