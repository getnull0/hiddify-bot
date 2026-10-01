"""Typed accessors for optional aiogram event fields."""

from aiogram.types import CallbackQuery, Message


class MissingEventDataError(Exception):
    """Raised when an update lacks the message or sender a handler needs."""


def message_of(cb: CallbackQuery) -> Message:
    """Return the accessible message attached to a callback query."""
    if not isinstance(cb.message, Message):
        raise MissingEventDataError("callback message is missing or inaccessible")
    return cb.message


def user_id_of(event: Message | CallbackQuery) -> int:
    """Return the Telegram id of the user who triggered the event."""
    if event.from_user is None:
        raise MissingEventDataError("event has no sender")
    return event.from_user.id


def data_of(cb: CallbackQuery) -> str:
    """Return the callback payload."""
    if cb.data is None:
        raise MissingEventDataError("callback has no data")
    return cb.data


def callback_arg(cb: CallbackQuery) -> str:
    """Return everything after the first colon of the callback payload."""
    return data_of(cb).split(":", 1)[1]


def text_of(msg: Message) -> str:
    """Return the stripped message text, or an empty string for non-text messages."""
    return (msg.text or "").strip()
