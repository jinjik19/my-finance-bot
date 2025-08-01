from aiogram.fsm.state import State, StatesGroup


class AddEnvelope(StatesGroup):
    choosing_name = State()


class AddCategory(StatesGroup):
    choosing_name = State()
    choosing_type = State()


class EditEnvelope(StatesGroup):
    waiting_for_new_name = State()
    envelope_id = State()


class EditCategory(StatesGroup):
    waiting_for_new_name = State()
    category_id = State()


class AddTransaction(StatesGroup):
    choosing_amount = State()
    choosing_category = State()
    choosing_envelope = State()


class MakeTransfer(StatesGroup):
    choosing_amount = State()
    choosing_envelope_from = State()
    choosing_envelope_to = State()


class ArchiveTransfer(StatesGroup):
    choosing_envelope_to = State()


class AddGoal(StatesGroup):
    choosing_name = State()
    choosing_target_amount = State()
    choosing_envelope = State()
    choosing_phase = State()


class EditGoal(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_amount = State()
    goal_id = State()


class AddPhase(StatesGroup):
    choosing_name = State()
    choosing_monthly_target = State()


class EditPhase(StatesGroup):
    choosing_action = State()
    waiting_for_new_name = State()
    waiting_for_new_target = State()
    phase_id = State()


class AddScheduledTask(StatesGroup):
    choosing_type = State()
    choosing_day = State()
    choosing_hour = State()

    # для напоминаний
    waiting_for_text = State()

    # для переводов
    waiting_for_amount = State()
    choosing_envelope_from = State()
    choosing_envelope_to = State()


class SetInitialBalance(StatesGroup):
    choosing_envelope = State()
    waiting_for_amount = State()


class CommonStates(StatesGroup):
    waiting_for_timezone = State()
