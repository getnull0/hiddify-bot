"""Domain predicates over the user dicts returned by the panel."""

from typing import Literal

from utils.types import JsonDict

UserStatus = Literal["blocked", "active", "inactive"]


def limit_gb(user: JsonDict) -> float:
    return float(user.get("usage_limit_GB") or 0.0)


def is_blocked(user: JsonDict) -> bool:
    """A user is blocked when disabled, or zeroed by older bot versions (limit 0)."""
    return user.get("enable") is False or limit_gb(user) == 0


def user_status(user: JsonDict) -> UserStatus:
    """Classify a user as blocked, active, or enabled but out of traffic or days."""
    if is_blocked(user):
        return "blocked"
    return "active" if user.get("is_active") else "inactive"
