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
    {"name": f"💰 Доход ({settings.user_1_username})", "is_savings": False, "owner_id_placeholder": settings.user_1_telegram_id},
    {"name": f"💰 Доход ({settings.user_2_username})", "is_savings": False, "owner_id_placeholder": settings.user_2_telegram_id},

    # Общие сберегательные конверты (owner_id=None)
    {"name": "🎯 Главная Цель", "is_savings": True, "owner_id_placeholder": None},
    {"name": "🛡️ Подушка безопасности", "is_savings": True, "owner_id_placeholder": None},
    {"name": "🏦 На пенсию", "is_savings": True, "owner_id_placeholder": None},
]

DEFAULT_CATEGORIES = {
    "income": ["💰 Зарплата", "🪙 Аванс", "🎁 Подарки", "🤝 Продажа", "🧾 Вычеты", "🏝️ Отпускные"],
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
    {"name": "Ипотека", "target_amount": 404613, "linked_envelope_name": "🎯 Главная Цель", "phase_name": "🎯 Фаза 1: Ипотека"},
    {"name": "Накопить на переезд", "target_amount": 3030000, "linked_envelope_name": "🎯 Главная Цель", "phase_name": "🚀 Фаза 2: Переезд"},
    {"name": "Купить машину", "target_amount": 2000000, "linked_envelope_name": "🎯 Главная Цель", "phase_name": "🏠 Фаза 3: Машина"},
    {"name": "Накопления на пенсию", "target_amount": 10000000, "linked_envelope_name": "🏦 На пенсию", "phase_name": "🏠 Фаза 3: Машина"},
]

DEFAULT_SCHEDULED_TASKS = [
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 5, "cron_hour": 18, "reminder_text": f"🔔 {settings.user_2_username}, придет зарплата. Пора занести ее в 💰 Доход ({settings.user_2_username})."},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 10, "cron_hour": 17, "reminder_text": f"🔔 {settings.user_1_username}, придвет зарплата. Пора занести ее в 💰 Доход ({settings.user_1_username})."},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 14, "cron_hour": 20, "reminder_text": f"🔔 СРОЧНО: Сегодня нужно оплатить ипотеку (65 000 ₽) из конверта 🎯 Главная Цель!"},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 20, "cron_hour": 18, "reminder_text": f"🔔 {settings.user_2_username}, придет аванс. Пора занести его в 💰 Доход ({settings.user_2_username})."},
    {"phase_name": "🎯 Фаза 1: Ипотека", "task_type": "reminder", "cron_day": 25, "cron_hour": 17, "reminder_text": f"🔔 {settings.user_1_username}, придет аванс. Пора занести его в 💰 Доход ({settings.user_1_username})."},

    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 5, "cron_hour": 18, "reminder_text": f"🔔 {settings.user_2_username}, придет зарплата. Пора занести ее в 💰 Доход ({settings.user_2_username})."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 10, "cron_hour": 17, "reminder_text": f"🔔 {settings.user_1_username}, придвет зарплата. Пора занести ее в 💰 Доход ({settings.user_1_username})."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 20, "cron_hour": 18, "reminder_text": f"🔔 {settings.user_2_username}, придет аванс. Пора занести его в 💰 Доход ({settings.user_2_username})."},
    {"phase_name": "🚀 Фаза 2: Переезд", "task_type": "reminder", "cron_day": 25, "cron_hour": 17, "reminder_text": f"🔔 {settings.user_1_username}, придет аванс. Пора занести его в 💰 Доход ({settings.user_1_username})."},

    {"phase_name": "🏠 Фаза 3: Машина", "task_type": "reminder", "cron_day": 5, "cron_hour": 18, "reminder_text": f"🔔 {settings.user_2_username}, придет зарплата. Пора занести его в 🏦 На пенсию и 🎯 Главная Цель."},
    {"phase_name": "🏠 Фаза 3: Машина", "task_type": "reminder", "cron_day": 20, "cron_hour": 18, "reminder_text": f"🔔 {settings.user_2_username}, придет аванс. Пора занести ее в 🏦 На пенсию и 🎯 Главная Цель."},
]


async def create_envelopes(repo: RepoHolder) -> dict:
    """Создает конверты и возвращает словарь 'имя -> id'."""
    all_items = await repo.envelope.get_all()
    existing_items = {item.name: item.id for item in all_items}

    user_tg_id_to_db_id = {}
    for tg_id in settings.allowed_telegram_ids:
        user_db = await repo.user.get_by_telegram_id(tg_id)

        if user_db:
            user_tg_id_to_db_id[tg_id] = user_db.id
            continue

        logging.warning(f"User with telegram_id {tg_id} not found in DB. Envelopes for them might not be created correctly.")

    for data in DEFAULT_ENVELOPES:
        envelope_name = data["name"]
        owner_tg_id = data.get("owner_id_placeholder")

        owner_db_id = None
        if owner_tg_id is not None:
            owner_db_id = user_tg_id_to_db_id.get(owner_tg_id)

            if owner_db_id is None:
                logging.error(f"Cannot find DB user ID for Telegram ID {owner_tg_id}. Skipping envelope {envelope_name}.")
                continue

        if envelope_name not in existing_items:
            new_item = await repo.envelope.create(
                name=envelope_name,
                is_savings=data["is_savings"],
                owner_id=owner_db_id,
            )
            existing_items[new_item.name] = new_item.id
            logging.info(f"Created Envelope: {envelope_name} (owner_id: {owner_db_id})")

    active_default_envelope_names = {env["name"] for env in DEFAULT_ENVELOPES}
    for old_envelope in all_items:
        if old_envelope.name not in active_default_envelope_names and old_envelope.is_active:
            await repo.envelope.update(old_envelope, is_active=False)
            logging.info(f"Deactivated old Envelope: {old_envelope.name}")

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
