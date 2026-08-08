from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS, ADMIN_USERNAME
from filters.admin import IsAdmin
from keyboards.inline import admin_main_kb, user_main_kb
from services.user_service import find_by_tg_id

router = Router()

_ADMIN_MENU_TEXT = "👋 <b>Hiddify Admin</b>\n\nВыбери действие:"


@router.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    # Обычный юзер — проверяем профиль
    if msg.from_user.id not in ADMIN_IDS:
        user = await find_by_tg_id(msg.from_user.id)
        if not user:
            contact = f"@{ADMIN_USERNAME}" if ADMIN_USERNAME else "администратору"
            await msg.answer(
                f"👋 Привет!\n\n"
                f"❌ Твой аккаунт не найден в системе.\n\n"
                f"Для подключения обратись к администратору: {contact}"
            )
            return
        limit = user.get("usage_limit_GB") or 0
        enabled = user.get("enable", True)
        if limit == 0 or not enabled:
            contact = f"@{ADMIN_USERNAME}" if ADMIN_USERNAME else "администратору"
            await msg.answer(
                f"👋 Привет!\n\n"
                f"⛔ Твой аккаунт заблокирован.\n\n"
                f"Обратись к администратору: {contact}"
            )
            return
    await msg.answer("👋 Привет!\n\nВыбери что тебе нужно:", reply_markup=user_main_kb())


@router.message(Command("admin"), IsAdmin())
async def admin_panel(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(_ADMIN_MENU_TEXT, reply_markup=admin_main_kb())


@router.callback_query(F.data == "close")
async def close(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    try:
        await cb.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "menu", IsAdmin())
async def menu_admin(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await cb.message.edit_text(_ADMIN_MENU_TEXT, reply_markup=admin_main_kb())


@router.callback_query(F.data == "user_menu")
async def menu_user(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("Выбери что тебе нужно:", reply_markup=user_main_kb())


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()
