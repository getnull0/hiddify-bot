"""Business logic for server status and system operations."""

import asyncio
import html
import re

from hiddify_bot.api import get_client
from hiddify_bot.api.client import API_ERRORS
from hiddify_bot.utils.types import JsonDict

_HTML_TAG_RE = re.compile(r"<[^>]+>")
# The panel renders ANSI logs as a full HTML page; drop its head, styles and scripts
_HTML_NOISE_RE = re.compile(r"<(head|style|script)\b.*?</\1>", re.DOTALL | re.IGNORECASE)


def _strip_html(text: str) -> str:
    return html.unescape(_HTML_TAG_RE.sub("", _HTML_NOISE_RE.sub("", text)))


async def get_status() -> JsonDict:
    return await get_client().get_server_status()


async def get_logs(filename: str) -> str:
    raw = await get_client().get_logs(filename)
    return _strip_html(raw).strip() or "(пусто)"


async def update_usage() -> None:
    await get_client().update_usage()


async def get_panel_info() -> JsonDict:
    client = get_client()
    info, me = await asyncio.gather(client.get_panel_info(), client.get_me())
    return {
        "version": info.get("version", "—"),
        "admin_name": me.get("name", "—"),
        "admin_mode": me.get("mode", "—"),
    }


async def get_stats() -> JsonDict:
    return await get_client().get_dashboard()


async def get_nodes() -> list[JsonDict]:
    """Remote nodes; empty when there are none or the panel does not support nodes."""
    try:
        return await get_client().list_nodes()
    except API_ERRORS:
        return []


async def ping_node(node_id: int) -> JsonDict:
    return await get_client().ping_node(node_id)


async def sync_node(node_id: int) -> None:
    await get_client().sync_node(node_id)
