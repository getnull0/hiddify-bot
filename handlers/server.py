from http import HTTPStatus

from aiogram import F, Router
from aiogram.types import CallbackQuery

import services.server_service as svc
from api.client import HiddifyApiError
from filters.admin import IsAdmin
from formatters import texts
from formatters.server import panel_info, server_status
from keyboards.inline import admin_main_kb, generic_back_kb, logs_menu_kb
from utils.html import esc, esc_tail
from utils.telegram import callback_arg, message_of

router = Router()
router.callback_query.filter(IsAdmin())

# Telegram caps a message at 4096 characters; leave room for the header and <pre> tags
_LOG_CHARS = 3500


@router.callback_query(F.data == "server_status")
async def status(cb: CallbackQuery) -> None:
    await cb.answer()
    data = await svc.get_status()
    await message_of(cb).edit_text(server_status(data), reply_markup=generic_back_kb())


@router.callback_query(F.data == "update_usage")
async def update_usage(cb: CallbackQuery) -> None:
    await cb.answer("⏳ Обновляю трафик…")
    await svc.update_usage()
    await message_of(cb).edit_text(
        f"{texts.ADMIN_MENU}\n\n✅ Трафик обновлён", reply_markup=admin_main_kb()
    )


@router.callback_query(F.data == "logs_menu")
async def logs_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    await message_of(cb).edit_text("📋 Выбери лог-файл:", reply_markup=logs_menu_kb())


@router.callback_query(F.data.startswith("logs:"))
async def logs_view(cb: CallbackQuery) -> None:
    filename = callback_arg(cb)
    try:
        content = await svc.get_logs(filename)
    except HiddifyApiError as exc:
        if exc.status != HTTPStatus.NOT_FOUND:
            raise
        content = "(файл не найден на сервере)"
    await cb.answer()
    await message_of(cb).edit_text(
        f"📋 <b>Лог: {esc(filename)}</b>\n\n<pre>{esc_tail(content, _LOG_CHARS)}</pre>",
        reply_markup=generic_back_kb(back_cb="logs_menu"),
    )


@router.callback_query(F.data == "panel_info")
async def info(cb: CallbackQuery) -> None:
    await cb.answer()
    data = await svc.get_panel_info()
    await message_of(cb).edit_text(panel_info(data), reply_markup=generic_back_kb())
