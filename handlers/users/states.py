"""FSM state groups for the user-management wizards."""

from aiogram.fsm.state import State, StatesGroup


class CreateUser(StatesGroup):
    name = State()
    days = State()
    limit_gb = State()
    tg_id = State()


class EditUser(StatesGroup):
    waiting = State()


class UnblockUser(StatesGroup):
    limit_gb = State()


class SetTgId(StatesGroup):
    waiting = State()


class SearchUser(StatesGroup):
    query = State()
