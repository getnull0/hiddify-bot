from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS
from filters.admin import IsAdmin
from keyboards.inline import admin_main_kb, user_main_kb

router = Router()


@router.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    # Обычный юзер — проверяем профиль
    if msg.from_user.id not in ADMIN_IDS:
        from services.user_service import find_by_tg_id
        user = await find_by_tg_id(msg.from_user.id)
        if not user:
            await msg.answer(
                "👋 Привет!\n\n"
                "❌ Твой аккаунт не найден в системе.\n\n"
                "Для подключения обратись к администратору: @VoidrixLab"
            )
            return
    await msg.answer("👋 Привет!\n\nВыбери что тебе нужно:", reply_markup=user_main_kb())


@router.message(Command("admin"), IsAdmin())
async def admin_panel(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("👋 <b>Hiddify Admin</b>\n\nВыбери действие:", reply_markup=admin_main_kb())


@router.callback_query(F.data == "close")
async def close(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await cb.message.delete()


@router.callback_query(F.data == "menu", IsAdmin())
async def menu_admin(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await cb.message.edit_text("👋 <b>Hiddify Admin</b>\n\nВыбери действие:", reply_markup=admin_main_kb())


@router.callback_query(F.data == "user_menu")
async def menu_user(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("Выбери что тебе нужно:", reply_markup=user_main_kb())


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()
