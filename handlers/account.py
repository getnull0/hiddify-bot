"""
Личный кабинет — работает и для админа (кнопка в меню),
и для обычного юзера (через user_menu).
"""
from urllib.parse import quote

from aiogram import Router, F
from aiogram.types import CallbackQuery, URLInputFile

import services.account_service as svc
import services.user_service as user_svc
from config import ADMIN_IDS
from filters.admin import IsAdmin
from formatters.user import account_card
from keyboards.inline import generic_back_kb, user_generic_back_kb, my_link_kb, my_account_kb, photo_close_kb


router = Router()


def _qr_url(sub_url: str) -> str:
    return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=10&data={quote(sub_url, safe='')}"


async def _render_account(cb: CallbackQuery, uuid: str, is_admin: bool):
    data = await svc.get_account(uuid)
    home = "menu" if is_admin else "user_menu"
    await cb.message.edit_text(account_card(data), reply_markup=my_account_kb(home_cb=home))


# ── Для администратора (кнопка "Мой аккаунт" в admin menu) ───────────────────

@router.callback_query(F.data == "admin_my_account", IsAdmin())
async def admin_my_account(cb: CallbackQuery):
    await cb.answer()
    user = await user_svc.find_by_tg_id(cb.from_user.id)
    if not user:
        await cb.message.edit_text(
            "❌ Твой Telegram ID не привязан ни к одному пользователю.\n\n"
            "Создай себе юзера через панель и укажи свой Telegram ID.",
            reply_markup=generic_back_kb(),
        )
        return
    await _render_account(cb, user["uuid"], is_admin=True)


# ── Для обычного юзера ────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_account")
async def my_account(cb: CallbackQuery):
    await cb.answer()
    user = await user_svc.find_by_tg_id(cb.from_user.id)
    if not user:
        await cb.message.edit_text(
            "❌ Аккаунт не найден.\nОбратись к администратору.",
            reply_markup=user_generic_back_kb(),
        )
        return
    await _render_account(cb, user["uuid"], is_admin=False)


@router.callback_query(F.data == "my_link")
async def my_link(cb: CallbackQuery):
    await cb.answer()
    user = await user_svc.find_by_tg_id(cb.from_user.id)
    if not user:
        await cb.message.edit_text("❌ Аккаунт не найден.", reply_markup=user_generic_back_kb())
        return
    data = await svc.get_account(user["uuid"])
    is_admin = cb.from_user.id in ADMIN_IDS
    back = "admin_my_account" if is_admin else "my_account"
    home = "menu" if is_admin else "user_menu"
    await cb.message.edit_text(
        f"🔑 <b>Ссылка подписки</b>\n\n"
        f"<code>{data['sub_url']}</code>\n\n"
        f"<i>Нажми на ссылку чтобы скопировать\n"
        f"или QR-код для сканирования</i>",
        reply_markup=my_link_kb(back_cb=back, home_cb=home),
    )


@router.callback_query(F.data == "my_qr")
async def my_qr(cb: CallbackQuery):
    await cb.answer()
    user = await user_svc.find_by_tg_id(cb.from_user.id)
    if not user:
        return
    data = await svc.get_account(user["uuid"])
    sub_url = data["sub_url"]
    await cb.message.answer_photo(
        URLInputFile(_qr_url(sub_url), filename="qr.png"),
        caption=f"📲 <b>Отсканируй QR-код</b>\n\nИли скопируй ссылку:\n<code>{sub_url}</code>",
        reply_markup=photo_close_kb(),
    )


@router.callback_query(F.data == "my_apps")
async def my_apps(cb: CallbackQuery):
    await cb.answer()
    user = await user_svc.find_by_tg_id(cb.from_user.id)
    if not user:
        await cb.message.edit_text("❌ Аккаунт не найден.", reply_markup=user_generic_back_kb())
        return
    from keyboards.inline import apps_kb
    is_admin = cb.from_user.id in ADMIN_IDS
    back = "admin_my_account" if is_admin else "my_account"
    home = "menu" if is_admin else "user_menu"
    await cb.message.edit_text(
        "📱 <b>Приложения для подключения</b>\n\n"
        "Нажми на приложение — скачаешь и настроишь через «Импорт подписки».\n\n"
        "<b>Hiddify</b> — рекомендуем, поддерживает все протоколы.\n"
        "<b>v2rayNG / NekoBox</b> — Android-альтернативы.\n"
        "<b>Streisand</b> — лучший выбор для iOS.",
        reply_markup=apps_kb(back_cb=back, home_cb=home),
    )
