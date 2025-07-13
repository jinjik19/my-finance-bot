import asyncio
import logging
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.settings import settings
from src.db.repo_holder import RepoHolder

logging.basicConfig(level=logging.INFO)

# --- Настройки генератора ---
START_DATE = date(2025, 1, 1)
END_DATE = date.today()


async def generate_data():
    """Главная функция для генерации тестовых данных."""
    logging.info(f"Starting test data generation from {START_DATE} to {END_DATE}...")
    engine = create_async_engine(str(settings.database_url))
    session_pool = async_sessionmaker(engine, expire_on_commit=False)

    async with session_pool() as session:
        repo = RepoHolder(session)

        # --- Получаем ID основных сущностей ---
        user1_id, user2_id = settings.allowed_telegram_ids
        user_me = await repo.user.get_by_telegram_id(user1_id)
        user_wife = await repo.user.get_by_telegram_id(user2_id)

        envelopes = {e.name: e for e in await repo.envelope.get_all()}
        categories = {c.name: c for c in await repo.category.get_all()}

        # Проверяем, что все необходимые для генерации сущности существуют
        required_envelopes = ["📥 Общий котел", "🛒 Переменные расходы", "🎯 Главная Цель"]
        required_categories = ["💰 Зарплата", "🪙 Аванс", "🛒 Продукты", "🎉 Развлечения"]

        if not all(k in envelopes for k in required_envelopes) or \
           not all(k in categories for k in required_categories) or \
           not user_me or not user_wife:
            logging.error("Не найдена инициализация seed.")
            return

        env_main = envelopes["📥 Общий котел"]
        env_variable = envelopes["🛒 Переменные расходы"]
        env_goal = envelopes["🎯 Главная Цель"]

        cat_salary = categories["💰 Зарплата"]
        cat_avans = categories["🪙 Аванс"]
        cat_products = categories["🛒 Продукты"]
        cat_fun = categories["🎉 Развлечения"]

        # --- Генерируем транзакции по дням ---
        logging.info("Генерация транзакций...")
        current_date = START_DATE
        while current_date <= END_DATE:
            # Доходы (симулируем ваш план)
            if current_date.day == 5:
                await repo.transaction.create(user_id=user_me.id, category_id=cat_avans.id, envelope_id=env_main.id, amount=Decimal("80000"), transaction_date=current_date, comment="Тестовый аванс")

            if current_date.day == 20:
                await repo.transaction.create(user_id=user_me.id, category_id=cat_salary.id, envelope_id=env_main.id, amount=Decimal("100000"), transaction_date=current_date, comment="Тестовая ЗП")

            if current_date.day == 10:
                await repo.transaction.create(user_id=user_wife.id, category_id=cat_avans.id, envelope_id=env_main.id, amount=Decimal("30000"), transaction_date=current_date, comment="Тестовый аванс (жена)")

            if current_date.day == 25:
                await repo.transaction.create(user_id=user_wife.id, category_id=cat_salary.id, envelope_id=env_main.id, amount=Decimal("31000"), transaction_date=current_date, comment="Тестовая ЗП (жена)")

            if current_date.day == 6:
                await repo.transfer.create(from_envelope_id=env_main.id, to_envelope_id=env_goal.id, amount=Decimal("32500"))

            if current_date.day == 21:
                await repo.transfer.create(from_envelope_id=env_main.id, to_envelope_id=env_goal.id, amount=Decimal("32500"))

            if current_date.weekday() in [0, 3]: # По понедельникам и четвергам
                amount = Decimal(random.randint(2500, 4500))
                await repo.transaction.create(user_id=random.choice([user_me.id, user_wife.id]), category_id=cat_products.id, envelope_id=env_variable.id, amount=amount, transaction_date=current_date, comment="Тестовая закупка")

            if current_date.weekday() in [4, 5]: # По пятницам и субботам
                amount = Decimal(random.randint(1500, 5000))
                await repo.transaction.create(user_id=random.choice([user_me.id, user_wife.id]), category_id=cat_fun.id, envelope_id=env_variable.id, amount=amount, transaction_date=current_date, comment="Тестовые развлечения")

            current_date += timedelta(days=1)

        logging.info("Пересчитываем балансы всех конвертов...")
        all_envelopes_list = await repo.envelope.get_all()

        for env in all_envelopes_list:
            total_in = await repo.transaction.get_total_for_envelope_by_type(env.id, 'income')
            total_out = await repo.transaction.get_total_for_envelope_by_type(env.id, 'expense')
            total_transfer_in = await repo.transfer.get_total_to_envelope(env.id)
            total_transfer_out = await repo.transfer.get_total_from_envelope(env.id)

            final_balance = (total_in - total_out) + (total_transfer_in - total_transfer_out)
            await repo.envelope.update(env, balance=final_balance)
            logging.info(f"Обновлен баланс для '{env.name}' до {final_balance:.2f} ₽")

    await engine.dispose()
    logging.info("Тестовые данные успешно сгенерированы.")


if __name__ == "__main__":
    asyncio.run(generate_data())
