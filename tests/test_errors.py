"""The error router: API failures, harmless Telegram races, and unexpected crashes."""

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery, EditMessageText

from tests.conftest import ADMIN_ID
from tests.fakes.panel import FakePanel
from tests.fakes.telegram import Harness


def bad_request(method, text: str) -> TelegramBadRequest:
    return TelegramBadRequest(method=method, message=text)


async def test_api_error_on_a_text_message_is_sent_as_a_message(bot: Harness, panel: FakePanel):
    await bot.press("user_search", ADMIN_ID)
    panel.fail_next(500, "boom")
    await bot.text("anything", ADMIN_ID)
    assert bot.last_text == "❌ Ошибка панели: boom"


async def test_unexpected_error_shows_a_generic_alert(bot: Harness, monkeypatch):
    async def explode(*_a, **_k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("services.server_service.get_status", explode)
    await bot.press("server_status", ADMIN_ID)
    assert bot.alerts == ["❌ Ошибка сервера, попробуй позже"]
    assert [r.getMessage() for r in bot.unexpected] == ["Unhandled error: kaboom"]
    bot.unexpected.clear()


async def test_unexpected_error_on_a_text_message(bot: Harness, monkeypatch):
    async def explode(*_a, **_k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("services.user_service.search", explode)
    await bot.press("user_search", ADMIN_ID)
    await bot.text("x", ADMIN_ID)
    assert bot.last_text == "❌ Ошибка сервера, попробуй позже"
    bot.unexpected.clear()


async def test_message_not_modified_is_ignored(bot: Harness, panel: FakePanel):
    original = bot.session.make_request

    async def not_modified(b, method, timeout=None):
        if isinstance(method, EditMessageText):
            raise bad_request(method, "Bad Request: message is not modified")
        return await original(b, method, timeout)

    bot.session.make_request = not_modified  # type: ignore[method-assign]
    await bot.press("server_status", ADMIN_ID)
    assert bot.alerts == []
    assert bot.unexpected == []


async def test_alert_falls_back_to_a_chat_message_when_the_query_expired(
    bot: Harness, panel: FakePanel
):
    original = bot.session.make_request

    async def expired(b, method, timeout=None):
        if isinstance(method, AnswerCallbackQuery) and method.show_alert:
            raise bad_request(method, "Bad Request: query is too old")
        return await original(b, method, timeout)

    bot.session.make_request = expired  # type: ignore[method-assign]
    panel.fail_next(500, "late failure")
    await bot.press("server_status", ADMIN_ID)
    assert bot.last_text == "❌ Ошибка панели: late failure"


@pytest.mark.parametrize("kind", ["message", "callback"])
async def test_notification_failures_never_propagate(bot: Harness, panel: FakePanel, kind):
    async def always_fail(b, method, timeout=None):
        raise bad_request(method, "Bad Request: chat not found")

    bot.session.make_request = always_fail  # type: ignore[method-assign]
    panel.fail_next(500, "x")
    if kind == "callback":
        await bot.press("server_status", ADMIN_ID)
    else:
        await bot.text("/start", ADMIN_ID)
    # Reaching this line means no exception escaped the dispatcher, whichever path failed
    bot.unexpected.clear()
