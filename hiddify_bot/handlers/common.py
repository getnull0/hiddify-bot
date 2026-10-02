"""Entry points and navigation shared by admins and regular users."""

import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from hiddify_bot.config import ADMIN_IDS, ADMIN_USERNAME
from hiddify_bot.filters.admin import IsAdmin
from hiddify_bot.formatters import texts
from hiddify_bot.keyboards.inline import admin_main_kb, user_main_kb
from hiddify_bot.services.user_service import find_by_tg_id
from hiddify_bot.utils.telegram import message_of, user_id_of
from hiddify_bot.utils.user_state import is_blocked

router = Router()


def _contact() -> str:
    return f"@{ADMIN_USERNAME}" if ADMIN_USERNAME else "администратору"


@router.message(Command("start"))
async def start(msg: Message, state: FSMContext) -> None:
    await state.clear()
    tg_id = user_id_of(msg)
    # Admins get the user menu too (they use the bot as users) plus a button to the panel.
    if tg_id not in ADMIN_IDS:
        user = await find_by_tg_id(tg_id)
        if not user:
            await msg.answer(
                "👋 Привет!\n\n"
                "❌ Твой аккаунт не найден в системе.\n\n"
                f"Для подключения обратись к администратору: {_contact()}"
            )
            return
        if is_blocked(user):
            await msg.answer(
                "👋 Привет!\n\n⛔ Твой аккаунт заблокирован.\n\n"
                f"Обратись к администратору: {_contact()}"
            )
            return
    await msg.answer(
        "👋 Привет!\n\nВыбери что тебе нужно:", reply_markup=user_main_kb(tg_id in ADMIN_IDS)
    )


@router.message(Command("admin"), IsAdmin())
async def admin_panel(msg: Message, state: FSMContext) -> None:
    await state.clear()
    await msg.answer(texts.ADMIN_MENU, reply_markup=admin_main_kb())


@router.callback_query(F.data == "close")
async def close(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await message_of(cb).delete()


@router.callback_query(F.data == "menu", IsAdmin())
async def menu_admin(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.clear()
    await message_of(cb).edit_text(texts.ADMIN_MENU, reply_markup=admin_main_kb())


@router.callback_query(F.data == "user_menu")
async def menu_user(cb: CallbackQuery) -> None:
    await cb.answer()
    await message_of(cb).edit_text(
        "Выбери что тебе нужно:", reply_markup=user_main_kb(user_id_of(cb) in ADMIN_IDS)
    )


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery) -> None:
    await cb.answer()
