"""Business logic for managing Hiddify users."""

from typing import Any

import api.hiddify as api
from utils.types import JsonDict


async def get_all() -> list[JsonDict]:
    return await api.get_users()


async def get(uuid: str) -> JsonDict:
    return await api.get_user(uuid)


async def create(name: str, days: int, limit_gb: float, tg_id: int | None) -> JsonDict:
    return await api.create_user(name=name, days=days, limit_gb=limit_gb, telegram_id=tg_id)


async def update(uuid: str, **kwargs: Any) -> JsonDict:
    return await api.update_user(uuid, **kwargs)


async def delete(uuid: str) -> JsonDict:
    return await api.delete_user(uuid)


async def block(uuid: str) -> JsonDict:
    """Block via a zero limit; leaves enable untouched so protocols are preserved."""
    return await api.update_user(uuid, usage_limit_GB=0)


async def unblock(uuid: str, limit_gb: float) -> JsonDict:
    return await api.update_user(uuid, usage_limit_GB=limit_gb)


async def reset_traffic(uuid: str) -> JsonDict:
    return await api.reset_user_traffic(uuid)


async def extend(uuid: str, days: int) -> JsonDict:
    return await api.extend_user(uuid, days)


async def search(query: str) -> list[JsonDict]:
    q = query.lower()
    users = await api.get_users()
    return [
        u
        for u in users
        if q in (u.get("name") or "").lower()
        or q == str(u.get("telegram_id") or "")
        or q in str(u.get("uuid") or "").lower()
    ]


async def find_by_tg_id(tg_id: int) -> JsonDict | None:
    return await api.find_user_by_telegram_id(tg_id)
