"""Parsers for user-typed numbers."""

import math

# The panel silently caps the traffic limit at one million GB.
MAX_LIMIT_GB = 1_000_000
MAX_DAYS = 36_500


def parse_finite_float(raw: str) -> float | None:
    """Parse a float, rejecting garbage, NaN and infinity."""
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_int(raw: str) -> int | None:
    """Parse an int, returning None on invalid input."""
    try:
        return int(raw)
    except ValueError:
        return None


def parse_limit_gb(raw: str) -> float | None:
    """Parse a traffic limit in GB; must be positive and within the panel cap."""
    value = parse_finite_float(raw)
    return value if value is not None and 0 < value <= MAX_LIMIT_GB else None


def parse_days(raw: str) -> int | None:
    """Parse a package length in days; at least one day."""
    value = parse_int(raw)
    return value if value is not None and 1 <= value <= MAX_DAYS else None


MAX_COMMENT_CHARS = 200


def parse_comment(raw: str) -> str | None:
    """A user note: 1 to 200 characters."""
    return raw if 1 <= len(raw) <= MAX_COMMENT_CHARS else None


def parse_telegram_id(raw: str) -> int | None:
    """Parse a Telegram user id; ids are positive integers."""
    value = parse_int(raw)
    return value if value is not None and value > 0 else None
