from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Category, Envelope, Goal, Phase


def get_envelopes_manage_menu() -> InlineKeyboardMarkup:
    """Создает меню для управления конвертами."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Список", callback_data="list_envelopes"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_envelope"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_envelope_menu"),
        InlineKeyboardButton(text="🗄️ Архивировать", callback_data="archive_envelope_menu"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_manage"))
    return builder.as_markup()


def get_categories_manage_menu() -> InlineKeyboardMarkup:
    """Создает меню для управления категориями."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Список", callback_data="list_categories"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_category"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_category_menu"),
        InlineKeyboardButton(text="🗄️ Архивировать", callback_data="archive_category_menu"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_manage"))
    return builder.as_markup()


def get_goals_manage_menu() -> InlineKeyboardMarkup:
    """Создает меню для управления целями."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Список целей", callback_data="list_goals"),
        InlineKeyboardButton(text="➕ Добавить цель", callback_data="add_goal"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_goal_menu"),
        InlineKeyboardButton(text="🗄️ Архивировать", callback_data="archive_goal_menu"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_manage"))
    return builder.as_markup()


def get_phases_manage_menu() -> InlineKeyboardMarkup:
    """Создает меню для управления фазами."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Список / Выбрать", callback_data="list_phases"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_phase"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_phase_menu"),
        InlineKeyboardButton(text="🗄️ Архивировать", callback_data="archive_phase_menu"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_manage"))
    return builder.as_markup()


def get_scheduler_manage_menu() -> InlineKeyboardMarkup:
    """Создает меню для управления задачами."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Список задач", callback_data="list_tasks"),
        InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_manage"))

    return builder.as_markup()


def get_task_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа новой задачи."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔔 Напоминание", callback_data="add_task_type:reminder"),
        InlineKeyboardButton(text="🤖 Авто-перевод", callback_data="add_task_type:auto_transfer"),
    )

    return builder.as_markup()


def get_edit_envelope_keyboard(envelope_id: int, is_savings: bool) -> InlineKeyboardMarkup:
    """Клавиатура для выбора, что именно редактировать в конверте."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_envelope_name:{envelope_id}"))
    builder.row(
        InlineKeyboardButton(
            text=f"🎯 Сделать {'не' if is_savings else ''}накопительным",
            callback_data=f"toggle_savings:envelope:{envelope_id}",
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ К меню конвертов", callback_data="manage_envelopes"))
    return builder.as_markup()


def get_edit_phase_keyboard(phase_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора, что именно редактировать в фазе."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Название", callback_data=f"edit_phase_name:{phase_id}"),
        InlineKeyboardButton(text="Месячную цель", callback_data=f"edit_phase_target:{phase_id}"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ К списку фаз", callback_data="list_phases"))

    return builder.as_markup()


def get_items_for_action_keyboard(
    items: list[Envelope | Category | Goal | Phase], action: str, entity_type: str
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора конкретного элемента для действия."""
    builder = InlineKeyboardBuilder()

    for item in items:
        builder.row(InlineKeyboardButton(text=item.name, callback_data=f"{action}:{entity_type}:{item.id}"))

    return builder.as_markup()


def get_phases_keyboard(phases: list[Phase], current_phase_id: int | None) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора текущей финансовой фазы."""
    builder = InlineKeyboardBuilder()

    for phase in phases:
        text = f"✅ {phase.name}" if phase.id == current_phase_id else phase.name
        builder.row(InlineKeyboardButton(text=text, callback_data=f"set_phase:{phase.id}"))

    return builder.as_markup()


category_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Доход", callback_data="category_type:income"),
            InlineKeyboardButton(text="Расход", callback_data="category_type:expense"),
        ]
    ]
)
