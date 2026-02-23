from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.text_decorations import html_decoration as hd

import services.server_service as svc
from filters.admin import IsAdmin
from formatters.server import server_status, panel_info
from keyboards.inline import logs_menu_kb, generic_back_kb

router = Router()
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "server_status")
async def status(cb: CallbackQuery):
    await cb.answer()
    data = await svc.get_status()
    await cb.message.edit_text(server_status(data), reply_markup=generic_back_kb())


@router.callback_query(F.data == "update_usage")
async def update_usage(cb: CallbackQuery):
    await cb.answer("✅ Трафик обновлён")
    await svc.update_usage()


@router.callback_query(F.data == "logs_menu")
async def logs_menu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("📋 Выбери лог-файл:", reply_markup=logs_menu_kb())


@router.callback_query(F.data.startswith("logs:"))
async def logs_view(cb: CallbackQuery):
    filename = cb.data.split(":", 1)[1]
    await cb.answer()
    content = await svc.get_logs(filename)
    await cb.message.edit_text(
        f"📋 <b>Лог: {filename}</b>\n\n<pre>{hd.quote(content)}</pre>",
        reply_markup=generic_back_kb(back_cb="logs_menu"),
    )


@router.callback_query(F.data == "panel_info")
async def info(cb: CallbackQuery):
    await cb.answer()
    data = await svc.get_panel_info()
    await cb.message.edit_text(panel_info(data), reply_markup=generic_back_kb())
