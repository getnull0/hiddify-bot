"""Rendering helpers shared by the user-management handlers."""

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from hiddify_bot.formatters.user import user_card
from hiddify_bot.keyboards.inline import user_actions_kb
from hiddify_bot.utils.telegram import message_of
from hiddify_bot.utils.types import JsonDict
from hiddify_bot.utils.user_state import is_blocked


async def current_list_page(state: FSMContext) -> int:
    """Page of the users list the admin came from, so Back returns to it."""
    return int((await state.get_data()).get("list_page", 0))


def _card(user: JsonDict, list_page: int, note: str) -> tuple[str, InlineKeyboardMarkup]:
    text = f"{note}\n\n{user_card(user)}" if note else user_card(user)
    return text, user_actions_kb(user["uuid"], is_blocked(user), list_page)


async def edit_card(cb: CallbackQuery, user: JsonDict, list_page: int, note: str = "") -> None:
    """Replace the callback's message with the user card."""
    text, markup = _card(user, list_page, note)
    await message_of(cb).edit_text(text, reply_markup=markup)


async def reply_card(msg: Message, user: JsonDict, list_page: int = 0, note: str = "") -> None:
    """Send the user card as a new message."""
    text, markup = _card(user, list_page, note)
    await msg.answer(text, reply_markup=markup)
