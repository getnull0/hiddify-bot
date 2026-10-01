"""Personal account built from admin endpoints (no per-user API key needed)."""

from datetime import date, datetime, timedelta

from api import get_client
from config import HIDDIFY_URL, HIDDIFY_USER_PATH
from utils.types import JsonDict


def _sub_url(user_uuid: str) -> str:
    return f"{HIDDIFY_URL}/{HIDDIFY_USER_PATH}/{user_uuid}/"


def _days_left(start_date_str: str | None, package_days: int) -> int:
    if not start_date_str:
        return package_days
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end = start + timedelta(days=package_days)
        return max(0, (end - date.today()).days)
    except ValueError:
        return package_days


def _expiry_date(start_date_str: str | None, package_days: int) -> str | None:
    if not start_date_str:
        return None
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        return str(start + timedelta(days=package_days))
    except ValueError:
        return None


async def get_account(user_uuid: str) -> JsonDict:
    """Return account data from admin/user/{uuid}/ and build the subscription URL locally."""
    user = await get_client().get_user(user_uuid)
    package_days = user.get("package_days") or 0
    start_date = user.get("start_date")
    last_online = user.get("last_online") or ""
    return {
        "name": user.get("name", "—"),
        "used": user.get("current_usage_GB") or 0.0,
        "total": user.get("usage_limit_GB") or 0.0,
        "days_left": _days_left(start_date, package_days),
        "expiry_date": _expiry_date(start_date, package_days),
        "last_online": None if (not last_online or last_online.startswith("0001")) else last_online,
        "mode": user.get("mode") or "no_reset",
        "sub_url": _sub_url(user_uuid),
    }
