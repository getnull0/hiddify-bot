"""Shared utility functions."""

from aiogram.utils.text_decorations import html_decoration as hd

_ELLIPSIS = "…"


def esc(val: object) -> str:
    """Escape a value for aiogram HTML parse mode."""
    return hd.quote(str(val)) if val else ""


def esc_tail(text: str, limit: int) -> str:
    """Escape text, keeping its tail so the escaped result is at most `limit` characters."""
    escaped = esc(text)
    if len(escaped) <= limit:
        return escaped
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if len(esc(text[-mid:])) + len(_ELLIPSIS) <= limit:
            low = mid
        else:
            high = mid - 1
    return _ELLIPSIS + esc(text[-low:]) if low else _ELLIPSIS
