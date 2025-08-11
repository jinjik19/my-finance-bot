from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import category_type_keyboard, get_items_for_action_keyboard
from src.bot.states import AddCategory, EditCategory
from src.db.repo_holder import RepoHolder

router = Router()


@router.callback_query(F.data == "list_categories")
async def list_categories(callback: CallbackQuery, repo: RepoHolder):
    categories = await repo.category.get_all_active()

    if not categories:
        await callback.answer("Активных категорий пока нет.", show_alert=True)
        return

    response_text = "Ваши активные категории:\n\n"

    for cat in categories:
        cat_type = "💰 Доход" if cat.type == "income" else "📈 Расход"
        response_text += f"🏷️ «{cat.name}» (Тип: {cat_type})\n"

    await callback.message.edit_text(response_text)
    await callback.answer()


@router.callback_query(F.data == "add_category")
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategory.choosing_name)
    await state.update_data(_original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите название для новой категории:")
    await callback.answer()


@router.callback_query(F.data == "edit_category_menu")
async def edit_category_menu(callback: CallbackQuery, repo: RepoHolder):
    categories = await repo.category.get_all_active()
    await callback.message.edit_text(
        "Выберите категорию для переименования:",
        reply_markup=get_items_for_action_keyboard(categories, "edit", "category"),
    )


@router.callback_query(F.data == "archive_category_menu")
async def archive_category_menu(callback: CallbackQuery, repo: RepoHolder):
    categories = await repo.category.get_all_active()
    await callback.message.edit_text(
        "Выберите категорию для архивации:",
        reply_markup=get_items_for_action_keyboard(categories, "archive", "category"),
    )


# --- FSM для добавления ---


@router.message(AddCategory.choosing_name)
async def add_category_name_chosen(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    original_message_id = data.get("_original_message_id")

    await state.update_data(category_name=message.text)
    await state.set_state(AddCategory.choosing_type)

    if original_message_id:
        await bot.edit_message_text(
            text="Теперь выберите тип категории:",
            chat_id=message.chat.id,
            message_id=original_message_id,
            reply_markup=category_type_keyboard,
        )


@router.callback_query(AddCategory.choosing_type, F.data.startswith("category_type:"))
async def add_category_type_chosen(callback: CallbackQuery, state: FSMContext, repo: RepoHolder):
    category_type = callback.data.split(":")[1]
    user_data = await state.get_data()
    category_name = user_data.get("category_name")

    await repo.category.create(name=category_name, type=category_type)
    await state.clear()

    await callback.message.edit_text(f"✅ Категория «{category_name}» успешно создана.")
    await callback.answer()


# --- Логика изменения и архивации ---


@router.callback_query(F.data.startswith("edit:category:"))
async def edit_category_start(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":")[2])
    await state.set_state(EditCategory.waiting_for_new_name)
    await state.update_data(category_id=category_id, _original_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите новое название для категории:")
    await callback.answer()


@router.message(EditCategory.waiting_for_new_name)
async def edit_category_name_chosen(message: Message, state: FSMContext, repo: RepoHolder, bot: Bot):
    data = await state.get_data()
    category = await repo.category.get_by_id(data.get("category_id"))
    original_message_id = data.get("_original_message_id")

    if category:
        await repo.category.update(category, name=message.text)

        if original_message_id:
            await bot.edit_message_text(
                text=f"✅ Название категории изменено на «{message.text}».",
                chat_id=message.chat.id,
                message_id=original_message_id,
            )

    await state.clear()


@router.callback_query(F.data.startswith("archive:category:"))
async def archive_category(callback: CallbackQuery, repo: RepoHolder):
    category_id = int(callback.data.split(":")[2])
    category = await repo.category.get_by_id(category_id)

    if category:
        await repo.category.update(category, is_active=False)
        await callback.message.edit_text(f"✅ Категория «{category.name}» архивирована.")

    await callback.answer()
