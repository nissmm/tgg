from aiogram.fsm.state import State, StatesGroup


class AssignRole(StatesGroup):
    waiting_for_id = State()


class RemoveRole(StatesGroup):
    waiting_for_id = State()


class NewHRRecord(StatesGroup):
    candidate_info = State()
    phone = State()
    username = State()
    interview_datetime = State()


class SelfApply(StatesGroup):
    candidate_info = State()
    phone = State()
    username = State()
    interview_datetime = State()


class EditRecord(StatesGroup):
    waiting_value = State()


class SetPlan(StatesGroup):
    waiting_value = State()


class ModeratorReplyTicket(StatesGroup):
    waiting_text = State()


class UserReplyTicket(StatesGroup):
    waiting_text = State()
