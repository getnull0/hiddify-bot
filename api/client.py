"""Async client for the Hiddify Panel admin REST API (v2), authenticated by admin UUID."""

import asyncio
import json
import time
from datetime import date
from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import aiohttp

from config import Settings
from utils.types import JsonDict

_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=15)
CACHE_TTL = 30.0
_MAX_DETAIL_CHARS = 200


class HiddifyApiError(Exception):
    """The panel answered with an error status or an unusable payload."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"{status}: {message}")
        self.status = status
        self.message = message


# Failures a handler can report to the admin instead of crashing.
API_ERRORS = (HiddifyApiError, aiohttp.ClientError, TimeoutError)


def describe_api_error(exc: BaseException) -> str:
    """Return a short human-readable (Russian) explanation of an API failure."""
    if isinstance(exc, HiddifyApiError):
        if exc.status == 403:
            return "доступ запрещён. Проверь HIDDIFY_ADMIN_UUID и HIDDIFY_PROXY_PATH"
        if exc.status == HTTPStatus.BAD_REQUEST and exc.message == "invalid request":
            return "панель не узнала адрес. Проверь HIDDIFY_PROXY_PATH (нужен админский путь)"
        return exc.message
    if isinstance(exc, TimeoutError):
        return "панель не отвечает (таймаут)"
    if isinstance(exc, aiohttp.ClientConnectorError):
        return "не удалось подключиться к панели. Проверь HIDDIFY_URL"
    return str(exc) or type(exc).__name__


def _error_message(body: str, status: int, reason: str) -> str:
    try:
        payload = json.loads(body)
    except ValueError:
        return reason or f"HTTP {status}"
    if not isinstance(payload, dict):
        return reason or f"HTTP {status}"
    message = str(payload.get("message") or reason or f"HTTP {status}")
    if detail := payload.get("detail"):
        message = f"{message} ({str(detail)[:_MAX_DETAIL_CHARS]})"
    return message


def _days_since(start_date: str | None) -> int:
    """Whole days elapsed since the panel-formatted start date (0 if not started)."""
    if not start_date:
        return 0
    try:
        return max(0, (date.today() - date.fromisoformat(start_date[:10])).days)
    except ValueError:
        return 0


def _user_path(uuid: str) -> str:
    return f"/admin/user/{quote(uuid, safe='')}/"


class HiddifyClient:
    """HTTP client with a shared session and a short-lived users cache."""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.api_base
        self._headers = {"Hiddify-API-Key": settings.admin_uuid, "Accept": "application/json"}
        # False skips certificate checks (self-signed / sslip.io setups)
        self._ssl = settings.verify_ssl
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()
        self._users: list[JsonDict] | None = None
        self._users_at = 0.0
        self._by_tg_id: dict[int, JsonDict] = {}

    # ── Transport ─────────────────────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(timeout=_TIMEOUT)
            return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: JsonDict | None = None,
        form: dict[str, str] | None = None,
        as_text: bool = False,
    ) -> Any:
        session = await self._get_session()
        async with session.request(
            method,
            f"{self._base}{path}",
            headers=self._headers,
            json=payload,
            data=form,
            ssl=self._ssl,
            allow_redirects=False,
        ) as resp:
            body = await resp.text()
            status = resp.status
            reason = resp.reason or ""
        if 300 <= status < 400:
            raise HiddifyApiError(
                status, "панель перенаправила запрос. Проверь HIDDIFY_URL и HIDDIFY_PROXY_PATH"
            )
        if status >= 400:
            raise HiddifyApiError(status, _error_message(body, status, reason))
        if method != "GET" and path.startswith("/admin/user"):
            self.invalidate_users()
        if as_text:
            return body
        try:
            return json.loads(body)
        except ValueError:
            raise HiddifyApiError(
                status, "панель вернула не JSON. Проверь HIDDIFY_URL и HIDDIFY_PROXY_PATH"
            ) from None

    async def _request_object(self, method: str, path: str, **kwargs: Any) -> JsonDict:
        result = await self._request(method, path, **kwargs)
        if not isinstance(result, dict):
            raise HiddifyApiError(200, "неожиданный формат ответа панели")
        return result

    # ── Users ─────────────────────────────────────────────────────────────────

    def invalidate_users(self) -> None:
        self._users = None

    async def list_users(self) -> list[JsonDict]:
        if self._users is not None and time.monotonic() - self._users_at < CACHE_TTL:
            return self._users
        users = await self._fetch_users()
        self._users = users
        self._users_at = time.monotonic()
        self._by_tg_id = {u["telegram_id"]: u for u in users if u.get("telegram_id")}
        return users

    async def _fetch_users(self) -> list[JsonDict]:
        try:
            result = await self._request("GET", "/admin/user/")
        except HiddifyApiError as exc:
            if exc.status != 404:
                raise
            # The panel answers 404 "You have no user" for an empty list; make sure the
            # panel is reachable and the credentials work before treating it as empty.
            await self.get_me()
            return []
        if not isinstance(result, list):
            raise HiddifyApiError(200, "неожиданный формат списка пользователей")
        return result

    async def get_user(self, uuid: str) -> JsonDict:
        return await self._request_object("GET", _user_path(uuid))

    async def find_user_by_telegram_id(self, tg_id: int) -> JsonDict | None:
        await self.list_users()
        return self._by_tg_id.get(tg_id)

    async def create_user(
        self,
        name: str,
        days: int = 30,
        limit_gb: float = 50,
        mode: str = "no_reset",
        telegram_id: int | None = None,
    ) -> JsonDict:
        payload: JsonDict = {
            "name": name,
            "package_days": days,
            "usage_limit_GB": limit_gb,
            "mode": mode,
            "enable": True,
        }
        if telegram_id:
            payload["telegram_id"] = telegram_id
        return await self._request_object("POST", "/admin/user/", payload=payload)

    async def update_user(self, uuid: str, **fields: Any) -> JsonDict:
        return await self._request_object("PATCH", _user_path(uuid), payload=fields)

    async def delete_user(self, uuid: str) -> JsonDict:
        return await self._request_object("DELETE", _user_path(uuid))

    async def reset_user_traffic(self, uuid: str) -> JsonDict:
        return await self.update_user(uuid, current_usage_GB=0)

    async def extend_user(self, uuid: str, days: int) -> JsonDict:
        """Add days on top of what is left, reviving an already expired package."""
        user = await self.get_user(uuid)
        package_days = user.get("package_days") or 0
        elapsed = _days_since(user.get("start_date"))
        return await self.update_user(uuid, package_days=max(package_days, elapsed) + days)

    # ── System ────────────────────────────────────────────────────────────────

    async def get_server_status(self) -> JsonDict:
        return await self._request_object("GET", "/admin/server_status/")

    async def update_usage(self) -> None:
        await self._request("GET", "/admin/update_user_usage/", as_text=True)

    async def get_logs(self, filename: str) -> str:
        result: str = await self._request(
            "POST", "/admin/log/", form={"file": filename}, as_text=True
        )
        return result

    async def get_me(self) -> JsonDict:
        return await self._request_object("GET", "/admin/me/")

    async def get_panel_info(self) -> JsonDict:
        return await self._request_object("GET", "/panel/info/")
