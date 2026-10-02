"""Read-only user screens: list, card, search results, subscription link, QR, apps."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, URLInputFile

import hiddify_bot.services.account_service as account_svc
import hiddify_bot.services.user_service as svc
from hiddify_bot.formatters import texts
from hiddify_bot.handlers.users.states import SearchUser
from hiddify_bot.handlers.users.views import current_list_page, edit_card, reply_card
from hiddify_bot.keyboards.inline import (
    apps_kb,
    fsm_cancel_kb,
    generic_back_kb,
    photo_nav_kb,
    user_link_kb,
    users_list_kb,
)
from hiddify_bot.utils.html import esc
from hiddify_bot.utils.qr import qr_url
from hiddify_bot.utils.telegram import callback_arg, message_of, text_of

router = Router()


@router.callback_query(F.data.startswith("users_list:"))
async def users_list(cb: CallbackQuery, state: FSMContext) -> None:
    page = int(callback_arg(cb))
    users = await svc.get_all()
    await cb.answer()
    await state.update_data(list_page=page)
    if not users:
        await message_of(cb).edit_text("Нет пользователей.", reply_markup=generic_back_kb())
        return
    await message_of(cb).edit_text(
        f"👥 <b>Пользователи</b> ({len(users)})\n\nВыбери для управления:",
        reply_markup=users_list_kb(users, page),
    )


@router.callback_query(F.data.startswith("user:"))
async def user_detail(cb: CallbackQuery, state: FSMContext) -> None:
    user = await svc.get(callback_arg(cb))
    await cb.answer()
    await edit_card(cb, user, await current_list_page(state))


@router.callback_query(F.data == "user_search")
async def search_start(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(SearchUser.query)
    await state.update_data(back_cb="menu")
    await message_of(cb).edit_text(
        "Введи имя, UUID или Telegram ID:", reply_markup=fsm_cancel_kb("menu")
    )


@router.message(SearchUser.query)
async def search_do(msg: Message, state: FSMContext) -> None:
    query = text_of(msg)
    if not query:
        await msg.answer(
            "❌ Введи имя, UUID или Telegram ID текстом:", reply_markup=fsm_cancel_kb()
        )
        return
    results = await svc.search(query)
    await state.clear()
    if not results:
        await msg.answer(
            f"🔍 По запросу «{esc(query)}» ничего не найдено.", reply_markup=generic_back_kb()
        )
    elif len(results) == 1:
        await reply_card(msg, results[0])
    else:
        await msg.answer(
            f"🔍 «{esc(query)}» — найдено: {len(results)}", reply_markup=users_list_kb(results, 0)
        )


@router.callback_query(F.data.startswith("user_link:"))
async def user_link(cb: CallbackQuery) -> None:
    uuid = callback_arg(cb)
    account = await account_svc.get_account(uuid)
    await cb.answer()
    await message_of(cb).edit_text(texts.link(account["sub_url"]), reply_markup=user_link_kb(uuid))


@router.callback_query(F.data.startswith("user_qr:"))
async def user_qr(cb: CallbackQuery) -> None:
    uuid = callback_arg(cb)
    sub_url = (await account_svc.get_account(uuid))["sub_url"]
    await cb.answer()
    await message_of(cb).answer_photo(
        URLInputFile(qr_url(sub_url), filename="qr.png"),
        caption=texts.qr_caption(sub_url, "QR-код подписки"),
        reply_markup=photo_nav_kb(back_cb=f"user_link:{uuid}", home_cb="menu"),
    )


@router.callback_query(F.data.startswith("user_apps:"))
async def user_apps(cb: CallbackQuery) -> None:
    await cb.answer()
    await message_of(cb).edit_text(
        texts.APPS, reply_markup=apps_kb(back_cb=f"user:{callback_arg(cb)}", home_cb="menu")
    )
