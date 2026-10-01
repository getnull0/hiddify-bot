"""One-tap user actions: block, unblock, reset traffic, extend, reset mode, delete."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import services.user_service as svc
from formatters.user import MODE_LABELS
from handlers.users.states import UnblockUser
from handlers.users.views import current_list_page, edit_card
from keyboards.inline import confirm_delete_kb, fsm_cancel_kb, generic_back_kb, user_mode_kb
from utils.telegram import callback_arg, data_of, message_of
from utils.user_state import limit_gb

router = Router()


@router.callback_query(F.data.startswith("user_block:"))
async def user_block(cb: CallbackQuery, state: FSMContext) -> None:
    user = await svc.block(callback_arg(cb))
    await cb.answer("⛔ Заблокирован")
    await edit_card(cb, user, await current_list_page(state))


@router.callback_query(F.data.startswith("user_unblock:"))
async def user_unblock(cb: CallbackQuery, state: FSMContext) -> None:
    uuid = callback_arg(cb)
    user = await svc.get(uuid)
    if limit_gb(user) > 0:
        user = await svc.unblock(uuid)
        await cb.answer("✅ Разблокирован")
        await edit_card(cb, user, await current_list_page(state))
        return
    # Zero limit (set by older bot versions): the admin has to pick a new one.
    await cb.answer()
    await state.set_state(UnblockUser.limit_gb)
    await state.update_data(uuid=uuid, back_cb=f"user:{uuid}")
    await message_of(cb).edit_text(
        "Введи новый лимит трафика в GB (например: 50):",
        reply_markup=fsm_cancel_kb(f"user:{uuid}"),
    )


@router.callback_query(F.data.startswith("user_reset:"))
async def user_reset(cb: CallbackQuery, state: FSMContext) -> None:
    user = await svc.reset_traffic(callback_arg(cb))
    await cb.answer("🔄 Трафик сброшен")
    await edit_card(cb, user, await current_list_page(state))


@router.callback_query(F.data.startswith("user_extend:"))
async def user_extend(cb: CallbackQuery, state: FSMContext) -> None:
    _, uuid, days = data_of(cb).split(":")
    user = await svc.extend(uuid, int(days))
    await cb.answer(f"⏱ +{days} дней")
    await edit_card(cb, user, await current_list_page(state))


@router.callback_query(F.data.startswith("user_set_mode:"))
async def set_mode_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    await message_of(cb).edit_text(
        "🔁 Выбери режим сброса трафика:", reply_markup=user_mode_kb(callback_arg(cb))
    )


@router.callback_query(F.data.startswith("user_mode:"))
async def set_mode_do(cb: CallbackQuery, state: FSMContext) -> None:
    _, uuid, mode = data_of(cb).split(":")
    if mode not in svc.USER_MODES:
        await cb.answer("❌ Неизвестный режим", show_alert=True)
        return
    user = await svc.update(uuid, mode=mode)
    await cb.answer(f"✅ {MODE_LABELS[mode]}")
    await edit_card(cb, user, await current_list_page(state))


@router.callback_query(F.data.startswith("user_delete_confirm:"))
async def delete_confirm(cb: CallbackQuery) -> None:
    await cb.answer()
    await message_of(cb).edit_text(
        "⚠️ Удалить пользователя? Это необратимо.",
        reply_markup=confirm_delete_kb(callback_arg(cb)),
    )


@router.callback_query(F.data.regexp(r"^user_delete:[^_]"))
async def delete_do(cb: CallbackQuery, state: FSMContext) -> None:
    await svc.delete(callback_arg(cb))
    await cb.answer("🗑 Удалён")
    list_page = await current_list_page(state)
    await message_of(cb).edit_text(
        "✅ Пользователь удалён.", reply_markup=generic_back_kb(back_cb=f"users_list:{list_page}")
    )
