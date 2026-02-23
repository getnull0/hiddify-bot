"""Унифицированные компоненты навигации и пагинации."""
from aiogram.types import InlineKeyboardButton


def nav_row(back_cb: str | None = None, home_cb: str = "menu") -> list[InlineKeyboardButton]:
    """Нижняя строка: [◀️ Назад] [🏠] [✕ Закрыть] — все синие."""
    row = []
    if back_cb:
        row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb, style="primary"))
    row.append(InlineKeyboardButton(text="🏠", callback_data=home_cb, style="primary"))
    row.append(InlineKeyboardButton(text="✕ Закрыть", callback_data="close", style="primary"))
    return row


def pagination_row(
    page: int, total_pages: int, cb_prefix: str
) -> list[InlineKeyboardButton] | None:
    """Строка пагинации: [◀️] [X/Y] [▶️]. None если страница одна."""
    if total_pages <= 1:
        return None
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(
            text="◀️", callback_data=f"{cb_prefix}:{page - 1}", style="primary"
        ))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(
            text="▶️", callback_data=f"{cb_prefix}:{page + 1}", style="primary"
        ))
    return row
