"""Business logic for server status and system operations."""

import asyncio
import html
import re

import api.hiddify as api
from utils.types import JsonDict

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_HTML_TAG_RE.sub("", text))


async def get_status() -> JsonDict:
    return await api.get_server_status()


async def get_logs(filename: str) -> str:
    raw = await api.get_logs(filename)
    result = _strip_html(raw).strip()
    if len(result) > 3800:
        result = "…" + result[-3800:]
    return result or "(пусто)"


async def update_usage() -> None:
    await api.update_usage()


async def get_panel_info() -> JsonDict:
    info, me = await asyncio.gather(api.get_panel_info(), api.get_me())
    return {
        "version": info.get("version", "—"),
        "admin_name": me.get("name", "—"),
        "admin_mode": me.get("mode", "—"),
    }
