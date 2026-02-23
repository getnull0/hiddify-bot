"""Бизнес-логика статуса сервера и системных операций."""
import asyncio
import html
import re
import api.hiddify as api


def _strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


async def get_status() -> dict:
    return await api.get_server_status()


async def get_logs(filename: str) -> str:
    raw = await api.get_logs(filename)
    result = _strip_html(raw).strip()
    if len(result) > 3800:
        result = "…" + result[-3800:]
    return result or "(пусто)"


async def update_usage() -> None:
    await api.update_usage()


async def get_panel_info() -> dict:
    info, me = await asyncio.gather(api.get_panel_info(), api.get_me())
    return {"version": info.get("version", "—"), "admin_name": me.get("name", "—"), "admin_mode": me.get("mode", "—")}
