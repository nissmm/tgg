from aiogram.fsm.state import State, StatesGroup


class AssignRole(StatesGroup):
    waiting_for_id = State()


class RemoveRole(StatesGroup):
    waiting_for_id = State()


class NewHRRecord(StatesGroup):
    recorded_by = State()
    candidate_info = State()
    phone = State()
    username = State()
    interview_date = State()
