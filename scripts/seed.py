import asyncio
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.settings import settings
from src.db.models import Base
from src.db.repo_holder import RepoHolder

logging.basicConfig(level=logging.INFO)

# --- ДАННЫЕ ДЛЯ ЗАПОЛНЕНИЯ ---
DEFAULT_ENVELOPES = [
    {"name": "📥 Общий котел", "is_savings": False},
    {"name": "🛡️ Подушка безопасности", "is_savings": True},
    {"name": "🧾 Постоянные расходы", "is_savings": False},
    {"name": "🛒 Переменные расходы", "is_savings": False},
    {"name": "🎯 Главная Цель", "is_savings": True},
    {"name": "🏦 На пенсию", "is_savings": True},
    {"name": "👨 Личные (Женя)", "is_savings": False},
    {"name": "👩‍🦱 Личные (Таня)", "is_savings": False},
]

DEFAULT_CATEGORIES = {
    "income": ["💰 Зарплата", "🪙 Аванс", "🎁 Подарки", "🤝 Продажа", "🧾 Вычеты"],
    "expense": [
        "🛒 Продукты", "🏠 Коммуналка", "🏦 Ипотека", "🚗 Транспорт", "😼 Боня", 
        "🛋️ Для дома", "🎉 Развлечения", "🧑‍💻 Личные расходы", "💊 Здоровье", "💳 Подписки",
    ],
}

DEFAULT_PHASES = [
    {"name": "🎯 Фаза 1: Ипотека", "monthly_target": 65000},
    {"name": "🚀 Фаза 2: Переезд", "monthly_target": 115000},
    {"name": "🏠 Фаза 3: Машина", "monthly_target": 75000},
]

DEFAULT_GOALS = [
    {"name": "Ипотека", "target_amount": 466000, "linked_envelope_name": "🎯 Главная Цель", "phase_name": "🎯 Фаза 1: Ипотека"},
    {"name": "Накопить на переезд", "target_amount": 2500000, "linked_envelope_name": "🎯 Главная Цель", "phase_name": "🚀 Фаза 2: Переезд"},
    {"name": "Купить машину", "target_amount": 2000000, "linked_envelope_name": "🎯 Главная Цель", "phase_name": "🏠 Фаза 3: Машина"},
    {"name": "Накопления на пенсию", "target_amount": 10000000, "linked_envelope_name": "🏦 На пенсию", "phase_name": "🏠 Фаза 3: Машина"},
]

DEFAULT_SCHEDULED_TASKS = [
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 5, "cron_hour": 18, "reminder_text": "🔔 Женя, придет зарплата. Пора занести его в 📥 Общий котел."},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 5, "cron_hour": 19, "amount": 32500, "from_envelope": "📥 Общий котел", "to_envelope": "🎯 Главная Цель"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 6, "cron_hour": 9, "amount": 5000, "from_envelope": "📥 Общий котел", "to_envelope": "🧾 Постоянные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 6, "cron_hour": 10, "amount": 17500, "from_envelope": "📥 Общий котел", "to_envelope": "🛒 Переменные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 6, "cron_hour": 11, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👨 Личные (Женя)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 6, "cron_hour": 12, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👩‍🦱 Личные (Таня)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 10, "cron_hour": 17, "reminder_text": "🔔 Таня, придвет зарплата. Пора занести его в 📥 Общий котел."},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 11, "cron_hour": 9, "amount": 17500, "from_envelope": "📥 Общий котел", "to_envelope": "🛒 Переменные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 11, "cron_hour": 10, "amount": 5000, "from_envelope": "📥 Общий котел", "to_envelope": "🧾 Постоянные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 11, "cron_hour": 11, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👨 Личные (Женя)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 11, "cron_hour": 12, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👩‍🦱 Личные (Таня)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 14, "cron_hour": 20, "reminder_text": "🔔 СРОЧНО: Сегодня нужно оплатить ипотеку (65 000 ₽) из конверта 🎯 Главная Цель!"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 20, "cron_hour": 18, "reminder_text": "🔔 Женя, придет аванс. Пора занести ее в 📥 Общий котел."},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 20, "cron_hour": 19, "amount": 32500, "from_envelope": "📥 Общий котел", "to_envelope": "🎯 Главная Цель"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 21, "cron_hour": 9, "amount": 5000, "from_envelope": "📥 Общий котел", "to_envelope": "🧾 Постоянные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 21, "cron_hour": 10, "amount": 17500, "from_envelope": "📥 Общий котел", "to_envelope": "🛒 Переменные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 21, "cron_hour": 11, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👨 Личные (Женя)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 21, "cron_hour": 12, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👩‍🦱 Личные (Таня)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 26, "cron_hour": 9, "amount": 5000, "from_envelope": "📥 Общий котел", "to_envelope": "🧾 Постоянные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 26, "cron_hour": 10, "amount": 17500, "from_envelope": "📥 Общий котел", "to_envelope": "🛒 Переменные расходы"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 26, "cron_hour": 11, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👨 Личные (Женя)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "auto_transfer", "cron_day": 26, "cron_hour": 12, "amount": 7500, "from_envelope": "📥 Общий котел", "to_envelope": "👩‍🦱 Личные (Таня)"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 25, "cron_hour": 17, "reminder_text": "🔔 Таня, придет аванс. Пора занести ее в 📥 Общий котел."},

    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 5, "cron_hour": 18, "reminder_text": "🔔 Женя, придет зарплата. Пора занести его в 📥 Общий котел."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 10, "cron_hour": 17, "reminder_text": "🔔 Таня, придвет зарплата. Пора занести его в 📥 Общий котел."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 20, "cron_hour": 18, "reminder_text": "🔔 Женя, придет аванс. Пора занести ее в 📥 Общий котел."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 25, "cron_hour": 17, "reminder_text": "🔔 Таня, придет аванс. Пора занести ее в 📥 Общий котел."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "auto_transfer", "cron_day": 5, "cron_hour": 18, "amount": 57500, "from_envelope": "📥 Общий котел", "to_envelope": "🎯 Главная Цель"},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "auto_transfer", "cron_day": 20, "cron_hour": 18, "amount": 57500, "from_envelope": "📥 Общий котел", "to_envelope": "🎯 Главная Цель"},

    {"phase_name": "🏠 Фаза 3: Машина", "task_type": "auto_transfer", "cron_day": 5, "cron_hour": 18, "amount": 20000, "from_envelope": "📥 Общий котел", "to_envelope": "🏦 На пенсию"},
    {"phase_name": "🏠 Фаза 3: Машина", "task_type": "auto_transfer", "cron_day": 5, "cron_hour": 18, "amount": 37500, "from_envelope": "📥 Общий котел", "to_envelope": "🎯 Главная Цель"},
    {"phase_name": "🏠 Фаза 3: Машина", "task_type": "auto_transfer", "cron_day": 20, "cron_hour": 16, "amount": 20000, "from_envelope": "📥 Общий котел", "to_envelope": "🏦 На пенсию"},
    {"phase_name": "🏠 Фаза 3: Машина", "task_type": "auto_transfer", "cron_day": 20, "cron_hour": 16, "amount": 37500, "from_envelope": "📥 Общий котел", "to_envelope": "🎯 Главная Цель"},
]


async def create_envelopes(repo: RepoHolder) -> dict:
    """Создает конверты и возвращает словарь 'имя -> id'."""
    all_items = await repo.envelope.get_all()
    existing_items = {item.name: item.id for item in all_items}

    for data in DEFAULT_ENVELOPES:
        if data["name"] not in existing_items:
            new_item = await repo.envelope.create(**data, owner_id=None)
            existing_items[new_item.name] = new_item.id
            logging.info(f"Created Envelope: {data['name']}")

    return existing_items

async def create_categories(repo: RepoHolder):
    """Создает категории."""
    all_items = await repo.category.get_all()
    existing_items = {item.name for item in all_items}

    for cat_type, cat_names in DEFAULT_CATEGORIES.items():
        for name in cat_names:
            if name not in existing_items:
                await repo.category.create(name=name, type=cat_type)
                logging.info(f"Created Category: {name}")

async def create_phases(repo: RepoHolder) -> dict:
    """Создает фазы и возвращает словарь 'имя -> id'."""
    all_items = await repo.phase.get_all()
    existing_items = {item.name: item.id for item in all_items}

    for data in DEFAULT_PHASES:
        if data["name"] not in existing_items:
            new_item = await repo.phase.create(**data)
            existing_items[new_item.name] = new_item.id
            logging.info(f"Created Phase: {data['name']}")

    return existing_items


async def create_goals(repo: RepoHolder, envelopes_map: dict, phases_map: dict):
    """Создает цели."""
    all_items = await repo.goal.get_all()
    existing_items = {item.name for item in all_items}

    for data in DEFAULT_GOALS:
        if data["name"] not in existing_items:
            envelope_id = envelopes_map.get(data["linked_envelope_name"])
            phase_id = phases_map.get(data["phase_name"])

            if envelope_id and phase_id:
                await repo.goal.create(
                    name=data["name"], target_amount=data["target_amount"],
                    linked_envelope_id=envelope_id, phase_id=phase_id
                )
                logging.info(f"Created Goal: {data['name']}")


async def create_system_state(repo: RepoHolder, phases_map: dict):
    """Создает начальное состояние системы."""
    system_state = await repo.state.get_by_id(1)

    if not system_state:
        first_phase_name = DEFAULT_PHASES[0]["name"]
        first_phase_id = phases_map.get(first_phase_name)

        if first_phase_id:
            await repo.state.create(id=1, current_phase_id=first_phase_id)
            logging.info("Initialized system state.")


async def create_scheduled_tasks(repo: RepoHolder, envelopes_map: dict, phases_map: dict):
    """Создает запланированные задачи на основе констант."""
    all_tasks = await repo.scheduled_task.get_all()
    existing_tasks = {
        f"{t.phase_id}-{t.cron_day}-{t.cron_hour}-{t.task_type}-{t.reminder_text or t.to_envelope_id}"
        for t in all_tasks
    }

    for data in DEFAULT_SCHEDULED_TASKS:
        phase_id = phases_map.get(data["phase_name"])

        if not phase_id:
            continue

        task_kwargs = {
            "phase_id": phase_id,
            "task_type": data["task_type"],
            "cron_day": str(data["cron_day"]),
            "cron_hour": data["cron_hour"],
        }

        key_suffix = ""

        if data["task_type"] == "reminder":
            task_kwargs["reminder_text"] = data["reminder_text"]
            key_suffix = data["reminder_text"]
        else:
            from_id = envelopes_map.get(data["from_envelope"])
            to_id = envelopes_map.get(data["to_envelope"])

            if not from_id or not to_id:
                continue

            task_kwargs["amount"] = Decimal(data["amount"])
            task_kwargs["from_envelope_id"] = from_id
            task_kwargs["to_envelope_id"] = to_id
            key_suffix = to_id

        task_key = f"{phase_id}-{data['cron_day']}-{data['cron_hour']}-{data['task_type']}-{key_suffix}"

        if task_key not in existing_tasks:
            await repo.scheduled_task.create(**task_kwargs)
            logging.info(f"Created Scheduled Task: {data}")


async def seed_data():
    logging.info("Starting data seeding...")
    engine = create_async_engine(str(settings.database_url))
    session_pool = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


    async with session_pool() as session:
        repo = RepoHolder(session)

        envelopes_map = await create_envelopes(repo)
        await create_categories(repo)
        phases_map = await create_phases(repo)
        await create_goals(repo, envelopes_map, phases_map)
        await create_system_state(repo, phases_map)
        await create_scheduled_tasks(repo, envelopes_map, phases_map)

    await engine.dispose()
    logging.info("Data seeding finished.")


if __name__ == "__main__":
    asyncio.run(seed_data())
