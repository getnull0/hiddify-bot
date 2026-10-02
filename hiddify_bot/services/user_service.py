"""Business logic for managing Hiddify users."""

from typing import Any

from hiddify_bot.api import get_client
from hiddify_bot.utils.types import JsonDict

USER_MODES = ("no_reset", "monthly", "weekly", "daily")


async def get_all() -> list[JsonDict]:
    return await get_client().list_users()


async def get(uuid: str) -> JsonDict:
    return await get_client().get_user(uuid)


async def create(name: str, days: int, limit_gb: float, tg_id: int | None) -> JsonDict:
    return await get_client().create_user(
        name=name, days=days, limit_gb=limit_gb, telegram_id=tg_id
    )


async def update(uuid: str, **fields: Any) -> JsonDict:
    return await get_client().update_user(uuid, **fields)


async def delete(uuid: str) -> JsonDict:
    return await get_client().delete_user(uuid)


async def block(uuid: str) -> JsonDict:
    """Disable the user; the panel drops them from the proxy cores immediately."""
    return await get_client().update_user(uuid, enable=False)


async def unblock(uuid: str, limit_gb: float | None = None) -> JsonDict:
    """Re-enable the user, optionally setting a new traffic limit."""
    fields: JsonDict = {"enable": True}
    if limit_gb is not None:
        fields["usage_limit_GB"] = limit_gb
    return await get_client().update_user(uuid, **fields)


async def reset_traffic(uuid: str) -> JsonDict:
    return await get_client().reset_user_traffic(uuid)


async def extend(uuid: str, days: int) -> JsonDict:
    return await get_client().extend_user(uuid, days)


async def search(query: str) -> list[JsonDict]:
    """Match by name or uuid substring, or by exact Telegram id."""
    q = query.strip().lower()
    if not q:
        return []
    return [
        u
        for u in await get_client().list_users()
        if q in (u.get("name") or "").lower()
        or q == str(u.get("telegram_id") or "")
        or q in str(u.get("uuid") or "").lower()
    ]


async def find_by_tg_id(tg_id: int) -> JsonDict | None:
    return await get_client().find_user_by_telegram_id(tg_id)
