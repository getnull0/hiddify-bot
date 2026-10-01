from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import CallbackQuery, Message

from middlewares import throttle
from middlewares.throttle import ThrottleMiddleware


def event_data(user_id: int | None) -> dict:
    return {"event_from_user": SimpleNamespace(id=user_id) if user_id is not None else None}


async def test_second_event_within_the_window_is_dropped():
    handler = AsyncMock(return_value="ok")
    mw = ThrottleMiddleware(rate=60)
    assert await mw(handler, object(), event_data(1)) == "ok"
    assert await mw(handler, object(), event_data(1)) is None
    assert handler.await_count == 1


async def test_users_are_throttled_independently():
    handler = AsyncMock(return_value="ok")
    mw = ThrottleMiddleware(rate=60)
    await mw(handler, object(), event_data(1))
    assert await mw(handler, object(), event_data(2)) == "ok"


async def test_zero_rate_never_blocks():
    handler = AsyncMock(return_value="ok")
    mw = ThrottleMiddleware(rate=0)
    for _ in range(3):
        assert await mw(handler, object(), event_data(1)) == "ok"


async def test_callbacks_get_a_hint_when_throttled():
    handler = AsyncMock()
    mw = ThrottleMiddleware(rate=60)
    callback = MagicMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    await mw(handler, callback, event_data(1))
    await mw(handler, callback, event_data(1))
    callback.answer.assert_awaited_once_with("⏳ Не так быстро", show_alert=False)


async def test_plain_messages_are_dropped_silently():
    handler = AsyncMock()
    mw = ThrottleMiddleware(rate=60)
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    await mw(handler, message, event_data(1))
    await mw(handler, message, event_data(1))
    message.answer.assert_not_called()


async def test_events_without_a_user_pass_through():
    handler = AsyncMock(return_value="ok")
    assert await ThrottleMiddleware(rate=60)(handler, object(), event_data(None)) == "ok"


async def test_memory_is_bounded(monkeypatch):
    monkeypatch.setattr(throttle, "_MAX_ENTRIES", 3)
    mw = ThrottleMiddleware(rate=60)
    handler = AsyncMock()
    for user_id in range(10):
        await mw(handler, object(), event_data(user_id))
    assert len(mw._last) == 3
    assert list(mw._last) == [7, 8, 9]


async def test_first_event_passes_even_right_after_boot(monkeypatch):
    # monotonic() is the system uptime, so a freshly booted host reports tiny values
    monkeypatch.setattr(throttle, "monotonic", lambda: 5.0)
    handler = AsyncMock(return_value="ok")
    assert await ThrottleMiddleware(rate=60)(handler, object(), event_data(1)) == "ok"
