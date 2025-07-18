import calendar
import datetime as dt
import logging
from decimal import Decimal

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from workalendar.europe import Russia

from src.core.settings import settings
from src.db.models.scheduled_task import ScheduledTask
from src.db.repo_holder import RepoHolder

# Глобальная переменная для хранения планировщика
scheduler = AsyncIOScheduler()

national_calendar = Russia()
# Дни, которые переносятся НАЗАД на последний рабочий день
DAYS_TO_MOVE_BACK = {5, 20}
# Дни, которые переносятся ВПЕРЁД на первый рабочий день
DAYS_TO_MOVE_FORWARD = {10, 25}


def is_weekend(date_obj: dt.date) -> bool:
    """Проверяет, является ли дата выходным (суббота или воскресенье)."""
    return date_obj.weekday() >= calendar.SATURDAY


def is_holiday(date_obj: dt.date) -> bool:
    """Проверяет, является ли дата официальным праздником."""
    return national_calendar.is_holiday(date_obj)


def find_nearest_workday(original_date: dt.date, move_forward: bool) -> dt.date:
    """Находит ближайший рабочий день, двигаясь вперед или назад."""
    current_date = original_date

    while is_weekend(current_date) or is_holiday(current_date):
        if move_forward:
            current_date += dt.timedelta(days=1)
        else:
            current_date -= dt.timedelta(days=1)

    return current_date


def get_corrected_day(original_day_of_month: int, task: ScheduledTask, tz: str) -> int:
    """Получаем корректный день для уведомленя"""
    now = dt.datetime.now(tz=tz) # Используем таймзону планировщика
    target_date_this_month = dt.date(now.year, now.month, original_day_of_month)

    if original_day_of_month in DAYS_TO_MOVE_BACK:
        # Если день выпадает на выходной, переносим НАЗАД
        if is_weekend(target_date_this_month):
            corrected_date = find_nearest_workday(target_date_this_month, move_forward=False)
            corrected_day = corrected_date.day
            logging.info(
                f"Задача (ID:{task.id}) на {original_day_of_month} перенесена НАЗАД на {corrected_day} из-за выходного."
            )
    elif original_day_of_month in DAYS_TO_MOVE_FORWARD:
        # Если день выпадает на выходной, переносим ВПЕРЁД
        if is_weekend(target_date_this_month):
            corrected_date = find_nearest_workday(target_date_this_month, move_forward=True)
            corrected_day = corrected_date.day
            logging.info(
                f"Задача (ID:{task.id}) на {original_day_of_month} перенесена ВПЕРЁД на {corrected_day} из-за выходного." # noqa: E501
            )
    else:
        corrected_day = original_day_of_month

    return corrected_date


async def send_reminder(bot: Bot, reminder_text: str, task_id: int | None = None):
    """Отправляет текстовое напоминание обоим пользователям."""
    if not reminder_text:
        return

    logging.info(f"Извлечение напоминаний: {reminder_text}")

    for user_id in settings.allowed_telegram_ids:
        try:
            await bot.send_message(user_id, reminder_text)
        except Exception as e:
            logging.error(f"Ошибка отправки напоминаня пользователю {user_id}: {e}")


async def perform_auto_transfer(bot: Bot, amount: Decimal, from_envelope_id: int, to_envelope_id: int) -> None:
    """Выполняет автоматический перевод и уведомляет пользователей."""
    engine = create_async_engine(str(settings.database_url))
    session_pool = async_sessionmaker(engine, expire_on_commit=False)

    async with session_pool() as session:
        repo = RepoHolder(session)
        env_from = await repo.envelope.get_by_id(from_envelope_id)
        env_to = await repo.envelope.get_by_id(to_envelope_id)

        if not env_from or not env_to:
            logging.error(f"Нет конвертов для auto_transfer: {from_envelope_id} или {to_envelope_id}")
            return

        logging.info(f"Извлечение auto_transfer: {amount} из '{env_from.name}' в '{env_to.name}'")

        if env_from.balance < amount:
            msg = f"⚠️ **Авто-перевод не выполнен!**\nНедостаточно средств на «{env_from.name}» для перевода {amount:.2f} ₽."  # noqa: E501
        else:
            await repo.transfer.create(from_envelope_id=env_from.id, to_envelope_id=env_to.id, amount=amount)
            await repo.envelope.update(env_from, balance=env_from.balance - amount)
            await repo.envelope.update(env_to, balance=env_to.balance + amount)
            msg = f"🤖 **Авто-перевод выполнен!**\n✅ {amount:.2f} ₽ переведено с «{env_from.name}» на «{env_to.name}»."

        for user_id in settings.allowed_telegram_ids:
            try:
                await bot.send_message(user_id, msg, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Failed to send auto_transfer notification to {user_id}: {e}")

    await engine.dispose()


async def reload_scheduler_jobs(bot: Bot, session_pool: async_sessionmaker):
    global scheduler
    scheduler.remove_all_jobs()

    async with session_pool() as session:
        repo = RepoHolder(session)
        system_state = await repo.state.get_by_id(1)

        if not system_state or not system_state.current_phase_id:
            logging.warning("Нет активных фаз. Планировщие пустой.")
            return

        user = None

        for user_id in settings.allowed_telegram_ids:
            user = await repo.user.get_by_telegram_id(user_id)

            if user:
                break

        try:
            tz = pytz.timezone(user.timezone if user and user.timezone else "UTC")
            scheduler.timezone = tz
            logging.info(f"Установлена таймзона: {tz}")
        except pytz.UnknownTimeZoneError:
            scheduler.timezone = pytz.utc
            logging.warning(f"Неизвестная таймзона '{user.timezone}', используем UTC.")

        tasks = await repo.scheduled_task.get_by_phase_id(system_state.current_phase_id)

        for task in tasks:
            if not task.is_active:
                continue

            job_func, job_kwargs = None, {"bot": bot}
            corrected_day = get_corrected_day(int(task.cron_day), task, tz)

            if task.task_type == "reminder":
                job_func = send_reminder
                job_kwargs["reminder_text"] = task.reminder_text
            elif task.task_type == "auto_transfer":
                job_func = perform_auto_transfer
                job_kwargs.update({
                    "amount": task.amount,
                    "from_envelope_id": task.from_envelope_id,
                    "to_envelope_id": task.to_envelope_id,
                })

            if job_func:
                scheduler.add_job(
                    job_func,
                    trigger="cron",
                    day=corrected_day,
                    hour=int(task.cron_hour),
                    kwargs=job_kwargs,
                    id=f"task_{task.id}",
                )

    active_jobs = scheduler.get_jobs()
    logging.info(f"Планировщик перезапустился с {len(active_jobs)} джобами для текущей фазы.")


def start_scheduler():
    global scheduler

    if not scheduler.running:
        scheduler.start()
        logging.info("Планировщик запущен.")
