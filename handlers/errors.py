"""Error handlers: API failures are shown to the admin, anything else is logged."""

import contextlib
import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ExceptionMessageFilter, ExceptionTypeFilter
from aiogram.types import ErrorEvent, Message, Update

from api.client import API_ERRORS, describe_api_error
from utils.html import esc

log = logging.getLogger(__name__)
router = Router()

_ALERT_MAX = 200  # Telegram limits callback alert text to 200 characters


async def _notify(update: Update, text: str) -> None:
    """Tell the user about a failure, via an alert for buttons or a message for text."""
    if cb := update.callback_query:
        try:
            await cb.answer(text[:_ALERT_MAX], show_alert=True)
        except TelegramBadRequest:
            # The callback was already answered (or expired); fall back to a chat message.
            if isinstance(cb.message, Message):
                with contextlib.suppress(Exception):
                    await cb.message.answer(esc(text))
    elif update.message:
        with contextlib.suppress(Exception):
            await update.message.answer(esc(text))


@router.errors(ExceptionMessageFilter(r"(?s).*message is not modified"))
async def message_not_modified(event: ErrorEvent) -> bool:
    """Pressing a button that re-renders identical content is harmless."""
    with contextlib.suppress(Exception):
        if event.update.callback_query:
            await event.update.callback_query.answer()
    return True


@router.errors(ExceptionTypeFilter(*API_ERRORS))
async def api_error(event: ErrorEvent) -> bool:
    reason = describe_api_error(event.exception)
    log.warning("Panel API error: %s", reason)
    await _notify(event.update, f"❌ Ошибка панели: {reason}")
    return True


@router.errors()
async def unexpected_error(event: ErrorEvent) -> bool:
    log.error("Unhandled error: %s", event.exception, exc_info=event.exception)
    await _notify(event.update, "❌ Ошибка сервера, попробуй позже")
    return True
