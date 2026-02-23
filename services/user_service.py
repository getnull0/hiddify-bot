"""Бизнес-логика управления пользователями Hiddify."""
import api.hiddify as api


async def get_all() -> list[dict]:
    return await api.get_users()


async def get(uuid: str) -> dict:
    return await api.get_user(uuid)


async def create(name: str, days: int, limit_gb: float, tg_id: int | None) -> dict:
    return await api.create_user(name=name, days=days, limit_gb=limit_gb, telegram_id=tg_id)


async def update(uuid: str, **kwargs) -> dict:
    return await api.update_user(uuid, **kwargs)


async def delete(uuid: str) -> dict:
    return await api.delete_user(uuid)


async def block(uuid: str) -> dict:
    """Блокировка через лимит 0 — не трогает enable, протоколы не слетают."""
    return await api.update_user(uuid, usage_limit_GB=0)


async def unblock(uuid: str, limit_gb: float) -> dict:
    return await api.update_user(uuid, usage_limit_GB=limit_gb)


async def reset_traffic(uuid: str) -> dict:
    return await api.reset_user_traffic(uuid)


async def extend(uuid: str, days: int) -> dict:
    return await api.extend_user(uuid, days)


async def search(query: str) -> list[dict]:
    q = query.lower()
    users = await api.get_users()
    return [
        u for u in users
        if q in u.get("name", "").lower()
        or q == str(u.get("telegram_id", ""))
        or q in str(u.get("uuid", "")).lower()
    ]


async def find_by_tg_id(tg_id: int) -> dict | None:
    return await api.find_user_by_telegram_id(tg_id)
