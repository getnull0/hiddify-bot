import asyncio
import ssl
import time
from typing import Any

import aiohttp

from config import HIDDIFY_ADMIN_UUID, HIDDIFY_PROXY_PATH, HIDDIFY_URL, HIDDIFY_VERIFY_SSL
from utils.types import JsonDict

# Timeout for all Hiddify API requests: 15s connect, 30s total
_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=15)

# Network-level failures that handlers report to the user as API errors
API_ERRORS = (aiohttp.ClientError, TimeoutError)

# SSL: verify certificates only if HIDDIFY_VERIFY_SSL=true;
# otherwise skip verification (self-signed / sslip.io without a trusted CA)
if HIDDIFY_VERIFY_SSL:
    _ssl_ctx = ssl.create_default_context()
else:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

# Pre-built constants — avoid dict/str allocation on every request
_ADMIN_HEADERS = {"Hiddify-API-Key": HIDDIFY_ADMIN_UUID, "Content-Type": "application/json"}
_FORM_HEADERS = {"Hiddify-API-Key": HIDDIFY_ADMIN_UUID}
_BASE = f"{HIDDIFY_URL}/{HIDDIFY_PROXY_PATH}/api/v2"

# One session per process, created lazily on the first request
_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()

# Users list cache
_users_cache: list[JsonDict] | None = None
_users_cache_time: float = 0.0
_users_by_tg_id: dict[int, JsonDict] | None = None
CACHE_TTL = 30.0  # Cache lifetime in seconds


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        async with _session_lock:
            if _session is None or _session.closed:
                _session = aiohttp.ClientSession(timeout=_TIMEOUT)
    return _session


async def close_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


async def _json(resp: aiohttp.ClientResponse) -> JsonDict:
    result: JsonDict = await resp.json()
    return result


async def _get(path: str, headers: JsonDict) -> JsonDict:
    session = await _get_session()
    async with session.get(f"{_BASE}{path}", headers=headers, ssl=_ssl_ctx) as resp:
        resp.raise_for_status()
        return await _json(resp)


async def _get_list(path: str, headers: JsonDict) -> list[JsonDict]:
    session = await _get_session()
    async with session.get(f"{_BASE}{path}", headers=headers, ssl=_ssl_ctx) as resp:
        resp.raise_for_status()
        result: list[JsonDict] = await resp.json()
        return result


async def _post(
    path: str, headers: JsonDict, data: JsonDict | None = None, form: JsonDict | None = None
) -> JsonDict:
    session = await _get_session()
    if form:
        async with session.post(
            f"{_BASE}{path}", headers=_FORM_HEADERS, data=form, ssl=_ssl_ctx
        ) as resp:
            resp.raise_for_status()
            return await _json(resp)
    else:
        async with session.post(f"{_BASE}{path}", headers=headers, json=data, ssl=_ssl_ctx) as resp:
            resp.raise_for_status()
            return await _json(resp)


async def _patch(path: str, headers: JsonDict, data: JsonDict) -> JsonDict:
    session = await _get_session()
    async with session.patch(f"{_BASE}{path}", headers=headers, json=data, ssl=_ssl_ctx) as resp:
        resp.raise_for_status()
        return await _json(resp)


async def _delete(path: str, headers: JsonDict) -> JsonDict:
    session = await _get_session()
    async with session.delete(f"{_BASE}{path}", headers=headers, ssl=_ssl_ctx) as resp:
        resp.raise_for_status()
        try:
            return await _json(resp)
        except (aiohttp.ContentTypeError, ValueError):
            return {}


# ── Admin: Users ──────────────────────────────────────────────────────────────


async def get_users() -> list[JsonDict]:
    global _users_cache, _users_cache_time, _users_by_tg_id
    now = time.time()
    if _users_cache is None or now - _users_cache_time > CACHE_TTL:
        _users_cache = await _get_list("/admin/user/", _ADMIN_HEADERS)
        _users_cache_time = now
        _users_by_tg_id = {u["telegram_id"]: u for u in _users_cache if u.get("telegram_id")}
    return _users_cache


async def get_user(uuid: str) -> JsonDict:
    return await _get(f"/admin/user/{uuid}/", _ADMIN_HEADERS)


async def create_user(
    name: str,
    days: int = 30,
    limit_gb: float = 50,
    mode: str = "no_reset",
    telegram_id: int | None = None,
) -> JsonDict:
    data: JsonDict = {
        "name": name,
        "package_days": days,
        "usage_limit_GB": limit_gb,
        "mode": mode,
        "enable": True,
    }
    if telegram_id:
        data["telegram_id"] = telegram_id
    res = await _post("/admin/user/", _ADMIN_HEADERS, data=data)
    global _users_cache
    _users_cache = None
    return res


async def update_user(uuid: str, **kwargs: Any) -> JsonDict:
    res = await _patch(f"/admin/user/{uuid}/", _ADMIN_HEADERS, data=kwargs)
    global _users_cache
    _users_cache = None
    return res


async def delete_user(uuid: str) -> JsonDict:
    res = await _delete(f"/admin/user/{uuid}/", _ADMIN_HEADERS)
    global _users_cache
    _users_cache = None
    return res


async def reset_user_traffic(uuid: str) -> JsonDict:
    res = await _patch(f"/admin/user/{uuid}/", _ADMIN_HEADERS, data={"current_usage_GB": 0})
    global _users_cache
    _users_cache = None
    return res


async def extend_user(uuid: str, days: int) -> JsonDict:
    user = await get_user(uuid)
    current = user.get("package_days") or 0
    res = await _patch(
        f"/admin/user/{uuid}/", _ADMIN_HEADERS, data={"package_days": current + days}
    )
    global _users_cache
    _users_cache = None
    return res


# ── Admin: System ─────────────────────────────────────────────────────────────


async def get_server_status() -> JsonDict:
    return await _get("/admin/server_status/", _ADMIN_HEADERS)


async def update_usage() -> None:
    session = await _get_session()
    async with session.get(
        f"{_BASE}/admin/update_user_usage/", headers=_ADMIN_HEADERS, ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()


async def get_logs(filename: str) -> str:
    session = await _get_session()
    async with session.post(
        f"{_BASE}/admin/log/", headers=_FORM_HEADERS, data={"file": filename}, ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()
        return await resp.text()


async def get_me() -> JsonDict:
    return await _get("/admin/me/", _ADMIN_HEADERS)


async def get_panel_info() -> JsonDict:
    return await _get("/panel/info/", _ADMIN_HEADERS)


# ── Helpers ───────────────────────────────────────────────────────────────────

# NOTE: /user/* endpoints (me, short, all-configs, apps) return 400 in Hiddify v11
# due to an auth middleware bug, so we use admin endpoints and build URLs manually.


async def find_user_by_telegram_id(tg_id: int) -> JsonDict | None:
    await get_users()
    return _users_by_tg_id.get(tg_id) if _users_by_tg_id else None
