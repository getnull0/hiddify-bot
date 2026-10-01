"""Parsers for user-typed numbers."""

import math


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
