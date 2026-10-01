"""In-process fake of the Hiddify Panel v14 admin API, mirroring the real panel's semantics."""

import html
import re
import uuid as uuidlib
from datetime import date, timedelta
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestServer

ADMIN_UUID = "00000000-0000-0000-0000-00000000aaaa"
PROXY_PATH = "adminpath"
MODES = {"no_reset", "monthly", "weekly", "daily"}
GB = 1024**3
LOG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
LOG_PAGE = (
    "<html><head><style>.ansi2html-content{display:inline}</style></head>"
    '<body><pre class="ansi2html-content">{body}</pre></body></html>'
)

_EDITABLE = {
    "name",
    "usage_limit_GB",
    "package_days",
    "mode",
    "start_date",
    "current_usage_GB",
    "comment",
    "telegram_id",
    "enable",
}


def json_error(status: int, message: str, detail: Any = None) -> web.Response:
    body: dict[str, Any] = {"message": message, "detail": detail or {}}
    return web.json_response(body, status=status)


def _is_active(user: dict[str, Any]) -> bool:
    """Same rule as the panel: enabled, within the traffic limit, and not expired."""
    if user["deleted"] or not user["enable"]:
        return False
    if user["usage_limit_GB"] < user["current_usage_GB"]:
        return False
    remaining = user["package_days"]
    if user["start_date"]:
        elapsed = (date.today() - date.fromisoformat(user["start_date"])).days
        remaining = user["package_days"] - elapsed
    return remaining >= 0


class FakePanel:
    def __init__(self, admin_uuid: str = ADMIN_UUID, proxy_path: str = PROXY_PATH) -> None:
        self.admin_uuid = admin_uuid
        self.proxy_path = proxy_path
        self.users: dict[str, dict[str, Any]] = {}
        self.logs: dict[str, str] = {"panel.log": "line one\nline <two> & three"}
        self.requests: list[tuple[str, str]] = []
        self.max_users: int | None = None
        self._forced_failure: tuple[int, str] | None = None
        self._forced_response: tuple[int, str, str] | None = None
        self._next_id = 1
        self._server: TestServer | None = None

    # ── Test controls ─────────────────────────────────────────────────────────

    def add_user(self, **fields: Any) -> dict[str, Any]:
        user: dict[str, Any] = {
            "uuid": str(uuidlib.uuid4()),
            "name": "User",
            "usage_limit_GB": 50.0,
            "package_days": 30,
            "mode": "no_reset",
            "last_online": "0001-01-01 00:00:00",
            "start_date": None,
            "current_usage_GB": 0.0,
            "comment": None,
            "telegram_id": None,
            "enable": True,
            "deleted": False,
            "id": self._next_id,
        }
        self._next_id += 1
        user.update(fields)
        user["is_active"] = _is_active(user)
        self.users[user["uuid"]] = user
        return user

    def fail_next(self, status: int, message: str) -> None:
        """Make the next API request fail with the given status and message."""
        self._forced_failure = (status, message)

    def respond_next(self, body: str, status: int = 200, content_type: str = "text/html") -> None:
        """Make the next authenticated request return an arbitrary raw response."""
        self._forced_response = (status, body, content_type)

    def count(self, method: str, path_suffix: str) -> int:
        return sum(1 for m, p in self.requests if m == method and p.endswith(path_suffix))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        assert self._server is not None
        return str(self._server.make_url("")).rstrip("/")

    async def start(self) -> None:
        app = web.Application(middlewares=[self._guard])
        prefix = f"/{self.proxy_path}/api/v2"
        app.router.add_get(f"{prefix}/admin/user/", self._list_users)
        app.router.add_post(f"{prefix}/admin/user/", self._create_user)
        app.router.add_get(f"{prefix}/admin/user/{{uuid}}/", self._get_user)
        app.router.add_patch(f"{prefix}/admin/user/{{uuid}}/", self._patch_user)
        app.router.add_delete(f"{prefix}/admin/user/{{uuid}}/", self._delete_user)
        app.router.add_get(f"{prefix}/admin/server_status/", self._server_status)
        app.router.add_get(f"{prefix}/admin/update_user_usage/", self._update_usage)
        app.router.add_post(f"{prefix}/admin/log/", self._log)
        app.router.add_get(f"{prefix}/admin/me/", self._me)
        app.router.add_get(f"{prefix}/panel/info/", self._info)
        app.router.add_route("*", "/{tail:.*}", self._unknown_path)
        self._server = TestServer(app)
        await self._server.start_server()

    async def stop(self) -> None:
        if self._server:
            await self._server.close()

    # ── Middleware ────────────────────────────────────────────────────────────

    @web.middleware
    async def _guard(self, request: web.Request, handler: Any) -> web.StreamResponse:
        self.requests.append((request.method, request.path))
        if self._forced_failure:
            status, message = self._forced_failure
            self._forced_failure = None
            return json_error(status, message)
        if request.headers.get("Hiddify-API-Key") != self.admin_uuid:
            return json_error(403, "Unathorized")
        if self._forced_response:
            status, body, content_type = self._forced_response
            self._forced_response = None
            return web.Response(status=status, text=body, content_type=content_type)
        return await handler(request)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _user_or_404(self, request: web.Request) -> dict[str, Any] | None:
        user = self.users.get(request.match_info["uuid"])
        return None if user is None or user["deleted"] else user

    async def _unknown_path(self, request: web.Request) -> web.Response:
        """The real panel answers 400 'invalid request' for an unknown proxy path."""
        return json_error(400, "invalid request")

    async def _list_users(self, request: web.Request) -> web.Response:
        users = [u for u in self.users.values() if not u["deleted"]]
        if not users:
            return json_error(404, "You have no user")
        return web.json_response(users)

    async def _create_user(self, request: web.Request) -> web.Response:
        data = await request.json()
        if self.max_users is not None and len(self.users) >= self.max_users:
            return json_error(400, f"User limit reached: max {self.max_users} users")
        problems = {}
        if not isinstance(data.get("name"), str) or not data["name"]:
            problems["name"] = ["Field required"]
        if data.get("mode", "no_reset") not in MODES:
            problems["mode"] = ["Invalid mode"]
        if problems:
            return json_error(422, "Validation error", {"json": problems})
        fields = {k: v for k, v in data.items() if k in _EDITABLE}
        return web.json_response(self.add_user(**fields))

    async def _get_user(self, request: web.Request) -> web.Response:
        user = self._user_or_404(request)
        return web.json_response(user) if user else json_error(404, "User not found")

    async def _patch_user(self, request: web.Request) -> web.Response:
        user = self._user_or_404(request)
        if not user:
            return json_error(404, "user not found")
        data = await request.json()
        for key, value in data.items():
            if key in _EDITABLE and value is not None:
                user[key] = value
        user["is_active"] = _is_active(user)
        return web.json_response(user)

    async def _delete_user(self, request: web.Request) -> web.Response:
        user = self._user_or_404(request)
        if not user:
            return json_error(404, "user not found")
        user["deleted"] = True
        return web.json_response({"status": 200, "msg": "ok"})

    async def _server_status(self, request: web.Request) -> web.Response:
        return web.json_response(
            {
                "stats": {
                    "system": {
                        "cpu_percent": 12.5,
                        "ram_used": 1.5,
                        "ram_total": 4.0,
                        "disk_used": 10.0,
                        "disk_total": 40.0,
                        "load_avg_1min": 0.1,
                        "load_avg_5min": 0.2,
                        "load_avg_15min": 0.3,
                        "total_connections": 42,
                        "total_unique_ips": 7,
                        "net_total_cumulative_GB": 123.4,
                    },
                    "top5": {"cpu": [["Hiddify", 3.0], ["xray", 1.5]]},
                },
                "usage_history": {
                    "today": {"usage": 2 * GB, "online": 1},
                    "total": {"usage": 100 * GB, "online": 3, "users": len(self.users)},
                },
            }
        )

    async def _update_usage(self, request: web.Request) -> web.Response:
        return web.Response(text="{}", content_type="text/html")

    async def _log(self, request: web.Request) -> web.Response:
        name = (await request.post()).get("file", "")
        if not isinstance(name, str) or not LOG_NAME_RE.match(name):
            return json_error(400, "Parameter issue: 'file'")
        if name not in self.logs:
            return json_error(404, "Invalid log file")
        return web.Response(
            text=LOG_PAGE.replace("{body}", html.escape(self.logs[name])), content_type="text/html"
        )

    async def _me(self, request: web.Request) -> web.Response:
        return web.json_response(
            {"name": "Owner", "mode": "super_admin", "uuid": self.admin_uuid, "can_add_admin": True}
        )

    async def _info(self, request: web.Request) -> web.Response:
        return web.json_response({"version": "14.0.0b5"})


def started_ago(days: int) -> str:
    """A panel-formatted start date `days` days in the past."""
    return (date.today() - timedelta(days=days)).isoformat()
