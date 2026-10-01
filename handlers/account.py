"""Personal account: works for admins (menu button) and regular users (user_menu)."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, URLInputFile

import services.account_service as svc
import services.user_service as user_svc
from config import ADMIN_IDS
from filters.admin import IsAdmin
from formatters import texts
from formatters.user import account_card
from keyboards.inline import (
    apps_kb,
    generic_back_kb,
    my_account_kb,
    my_link_kb,
    photo_nav_kb,
    proxy_kb,
    user_generic_back_kb,
)
from utils.qr import qr_url
from utils.telegram import message_of, user_id_of
from utils.types import JsonDict

router = Router()

_ADMIN_NOT_LINKED = (
    "❌ Твой Telegram ID не привязан ни к одному пользователю.\n\n"
    "Создай себе юзера через панель и укажи свой Telegram ID."
)
_USER_NOT_FOUND = "❌ Аккаунт не найден.\nОбратись к администратору."


def _nav(cb: CallbackQuery) -> tuple[str, str]:
    """Back and home callbacks for the viewer: admins and users have different menus."""
    if user_id_of(cb) in ADMIN_IDS:
        return "admin_my_account", "menu"
    return "my_account", "user_menu"


async def _own_user(cb: CallbackQuery) -> JsonDict | None:
    return await user_svc.find_by_tg_id(user_id_of(cb))


async def _show_account(cb: CallbackQuery) -> None:
    await cb.answer()
    user = await _own_user(cb)
    _, home = _nav(cb)
    if not user:
        text = _ADMIN_NOT_LINKED if home == "menu" else _USER_NOT_FOUND
        kb = generic_back_kb() if home == "menu" else user_generic_back_kb()
        await message_of(cb).edit_text(text, reply_markup=kb)
        return
    data = await svc.get_account(user["uuid"])
    await message_of(cb).edit_text(
        account_card(data), reply_markup=my_account_kb(home_cb=home, proxy=data["telegram_proxy"])
    )


@router.callback_query(F.data == "admin_my_account", IsAdmin())
async def admin_my_account(cb: CallbackQuery) -> None:
    await _show_account(cb)


@router.callback_query(F.data == "my_account")
async def my_account(cb: CallbackQuery) -> None:
    await _show_account(cb)


@router.callback_query(F.data == "my_link")
async def my_link(cb: CallbackQuery) -> None:
    await cb.answer()
    user = await _own_user(cb)
    if not user:
        await message_of(cb).edit_text(_USER_NOT_FOUND, reply_markup=user_generic_back_kb())
        return
    data = await svc.get_account(user["uuid"])
    back, home = _nav(cb)
    await message_of(cb).edit_text(
        texts.link(data["sub_url"]), reply_markup=my_link_kb(back_cb=back, home_cb=home)
    )


@router.callback_query(F.data == "my_qr")
async def my_qr(cb: CallbackQuery) -> None:
    await cb.answer()
    user = await _own_user(cb)
    if not user:
        await message_of(cb).answer(_USER_NOT_FOUND)
        return
    sub_url = (await svc.get_account(user["uuid"]))["sub_url"]
    _, home = _nav(cb)
    await message_of(cb).answer_photo(
        URLInputFile(qr_url(sub_url), filename="qr.png"),
        caption=texts.qr_caption(sub_url, "Отсканируй QR-код"),
        reply_markup=photo_nav_kb(back_cb="my_link", home_cb=home),
    )


@router.callback_query(F.data == "my_proxy")
async def my_proxy(cb: CallbackQuery) -> None:
    await cb.answer()
    user = await _own_user(cb)
    if not user:
        await message_of(cb).edit_text(_USER_NOT_FOUND, reply_markup=user_generic_back_kb())
        return
    proxies = await svc.get_telegram_proxies(user["uuid"])
    back, home = _nav(cb)
    if not proxies:
        await message_of(cb).edit_text(
            "📡 Прокси для Telegram пока не включён администратором.",
            reply_markup=generic_back_kb(back_cb=back, home_cb=home),
        )
        return
    await message_of(cb).edit_text(texts.PROXY, reply_markup=proxy_kb(proxies, back, home))


@router.callback_query(F.data == "my_apps")
async def my_apps(cb: CallbackQuery) -> None:
    await cb.answer()
    if not await _own_user(cb):
        await message_of(cb).edit_text(_USER_NOT_FOUND, reply_markup=user_generic_back_kb())
        return
    back, home = _nav(cb)
    await message_of(cb).edit_text(texts.APPS, reply_markup=apps_kb(back_cb=back, home_cb=home))
