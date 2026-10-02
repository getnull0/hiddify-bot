"""Environment-driven settings, validated once at startup."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self
from urllib.parse import urlparse

from dotenv import load_dotenv

_REQUIRED = (
    "BOT_TOKEN",
    "HIDDIFY_URL",
    "HIDDIFY_PROXY_PATH",
    "HIDDIFY_USER_PATH",
    "HIDDIFY_ADMIN_UUID",
    "ADMIN_IDS",
)
DEFAULT_QR_API_URL = "https://api.qrserver.com/v1/create-qr-code/"


class ConfigError(ValueError):
    """Raised when the environment does not describe a usable configuration."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    hiddify_url: str
    proxy_path: str
    user_path: str
    admin_uuid: str
    admin_ids: frozenset[int]
    admin_username: str
    qr_api_url: str
    verify_ssl: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Self:
        missing = [k for k in _REQUIRED if not env.get(k, "").strip()]
        if missing:
            raise ConfigError(f"Missing required env vars: {', '.join(missing)}. See .env.example")

        url = env["HIDDIFY_URL"].strip().rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError("HIDDIFY_URL must look like https://panel.example.com")

        return cls(
            bot_token=env["BOT_TOKEN"].strip(),
            hiddify_url=url,
            proxy_path=env["HIDDIFY_PROXY_PATH"].strip().strip("/"),
            user_path=env["HIDDIFY_USER_PATH"].strip().strip("/"),
            admin_uuid=env["HIDDIFY_ADMIN_UUID"].strip(),
            admin_ids=_parse_admin_ids(env["ADMIN_IDS"]),
            admin_username=env.get("ADMIN_USERNAME", "").strip().lstrip("@"),
            qr_api_url=env.get("QR_API_URL", "").strip() or DEFAULT_QR_API_URL,
            verify_ssl=env.get("HIDDIFY_VERIFY_SSL", "false").strip().lower() == "true",
        )

    @property
    def api_base(self) -> str:
        return f"{self.hiddify_url}/{self.proxy_path}/api/v2"


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            raise ConfigError(f"ADMIN_IDS must be comma-separated integers, got {part!r}") from None
    if not ids:
        raise ConfigError("ADMIN_IDS must contain at least one Telegram user id")
    return frozenset(ids)


def _load() -> Settings:
    load_dotenv()
    try:
        return Settings.from_env(os.environ)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc


settings = _load()

# Module-level aliases keep call sites short.
BOT_TOKEN = settings.bot_token
HIDDIFY_URL = settings.hiddify_url
HIDDIFY_USER_PATH = settings.user_path
ADMIN_IDS = settings.admin_ids
ADMIN_USERNAME = settings.admin_username
QR_API_URL = settings.qr_api_url
