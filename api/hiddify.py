import aiohttp
import ssl
from typing import Any
from config import HIDDIFY_URL, HIDDIFY_PROXY_PATH, HIDDIFY_ADMIN_UUID, HIDDIFY_VERIFY_SSL


# SSL: если HIDDIFY_VERIFY_SSL=true — используем стандартную проверку (Let's Encrypt)
# иначе отключаем (self-signed / sslip.io без доверенного CA)
if HIDDIFY_VERIFY_SSL:
    _ssl_ctx = ssl.create_default_context()
else:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

# Одна сессия на весь процесс — создаётся при первом запросе
_session: aiohttp.ClientSession | None = None


def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def close_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


def _admin_headers() -> dict:
    return {"Hiddify-API-Key": HIDDIFY_ADMIN_UUID, "Content-Type": "application/json"}


def _user_headers(user_uuid: str) -> dict:
    return {"Hiddify-API-Key": user_uuid, "Content-Type": "application/json"}


def _base() -> str:
    return f"{HIDDIFY_URL}/{HIDDIFY_PROXY_PATH}/api/v2"


async def _get(path: str, headers: dict) -> Any:
    session = _get_session()
    async with session.get(
        f"{_base()}{path}", headers=headers, ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()
        return await resp.json()


async def _post(path: str, headers: dict, data: dict = None, form: dict = None) -> Any:
    session = _get_session()
    if form:
        form_headers = {k: v for k, v in headers.items() if k != "Content-Type"}
        async with session.post(
            f"{_base()}{path}", headers=form_headers, data=form, ssl=_ssl_ctx
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    else:
        async with session.post(
            f"{_base()}{path}", headers=headers, json=data, ssl=_ssl_ctx
        ) as resp:
            resp.raise_for_status()
            return await resp.json()


async def _patch(path: str, headers: dict, data: dict) -> Any:
    session = _get_session()
    async with session.patch(
        f"{_base()}{path}", headers=headers, json=data, ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()
        return await resp.json()


async def _delete(path: str, headers: dict) -> Any:
    session = _get_session()
    async with session.delete(
        f"{_base()}{path}", headers=headers, ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()
        try:
            return await resp.json()
        except Exception:
            return {}


# ── Admin: Users ──────────────────────────────────────────────────────────────

async def get_users() -> list[dict]:
    return await _get("/admin/user/", _admin_headers())


async def get_user(uuid: str) -> dict:
    return await _get(f"/admin/user/{uuid}/", _admin_headers())


async def create_user(name: str, days: int = 30, limit_gb: float = 50,
                      mode: str = "no_reset", telegram_id: int = None) -> dict:
    data: dict = {
        "name": name,
        "package_days": days,
        "usage_limit_GB": limit_gb,
        "mode": mode,
        "enable": True,
    }
    if telegram_id:
        data["telegram_id"] = telegram_id
    return await _post("/admin/user/", _admin_headers(), data=data)


async def update_user(uuid: str, **kwargs) -> dict:
    return await _patch(f"/admin/user/{uuid}/", _admin_headers(), data=kwargs)


async def delete_user(uuid: str) -> dict:
    return await _delete(f"/admin/user/{uuid}/", _admin_headers())


async def reset_user_traffic(uuid: str) -> dict:
    return await _patch(
        f"/admin/user/{uuid}/", _admin_headers(),
        data={"current_usage_GB": 0}
    )


async def toggle_user(uuid: str, enable: bool) -> dict:
    return await _patch(
        f"/admin/user/{uuid}/", _admin_headers(),
        data={"enable": enable}
    )


async def extend_user(uuid: str, days: int) -> dict:
    user = await get_user(uuid)
    current = user.get("package_days") or 0
    return await _patch(
        f"/admin/user/{uuid}/", _admin_headers(),
        data={"package_days": current + days}
    )


# ── Admin: System ─────────────────────────────────────────────────────────────

async def get_server_status() -> dict:
    return await _get("/admin/server_status/", _admin_headers())


async def update_usage() -> None:
    session = _get_session()
    async with session.get(
        f"{_base()}/admin/update_user_usage/", headers=_admin_headers(), ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()  # endpoint возвращает text/html, не JSON


async def get_logs(filename: str) -> str:
    session = _get_session()
    headers = {k: v for k, v in _admin_headers().items() if k != "Content-Type"}
    async with session.post(
        f"{_base()}/admin/log/", headers=headers, data={"file": filename}, ssl=_ssl_ctx
    ) as resp:
        resp.raise_for_status()
        return await resp.text()


async def get_me() -> dict:
    return await _get("/admin/me/", _admin_headers())


async def get_panel_info() -> dict:
    return await _get("/panel/info/", _admin_headers())


# ── Helpers ───────────────────────────────────────────────────────────────────
# NOTE: /user/* endpoints (me, short, all-configs, apps) возвращают 400 в Hiddify v11
# из-за бага в auth middleware. Используем admin endpoints + строим URL вручную.

async def find_user_by_telegram_id(tg_id: int) -> dict | None:
    users = await get_users()
    for u in users:
        if u.get("telegram_id") == tg_id:
            return u
    return None
