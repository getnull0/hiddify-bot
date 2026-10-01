"""Shared utility functions."""

from aiogram.utils.text_decorations import html_decoration as hd


def esc(val: object) -> str:
    """Escape a value for aiogram HTML parse mode."""
    return hd.quote(str(val)) if val else ""
