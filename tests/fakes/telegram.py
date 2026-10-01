"""A fake Telegram Bot API and a harness that feeds real updates through the real dispatcher."""

import itertools
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    GetMe,
    SendMessage,
    SendPhoto,
    TelegramMethod,
)
from aiogram.types import CallbackQuery, Chat, Message, PhotoSize, Update, User

BOT_ID = 42


class FakeSession(BaseSession):
    """Records every Bot API call and answers with plausible results."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self._message_ids = itertools.count(1000)

    async def close(self) -> None:
        return None

    async def stream_content(  # type: ignore[override,misc]
        self, url: str, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[bytes, None]:
        yield b""

    async def make_request(
        self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, SendMessage | EditMessageText | SendPhoto):
            return Message(
                message_id=next(self._message_ids),
                date=datetime.now(UTC),
                chat=Chat(id=getattr(method, "chat_id", 0) or 0, type="private"),
                text=getattr(method, "text", None),
            )
        if isinstance(method, GetMe):
            return User(id=BOT_ID, is_bot=True, first_name="Bot", username="test_bot")
        return True


class Harness:
    """Drives the dispatcher the way Telegram would: text messages and button presses."""

    def __init__(self, dp: Dispatcher, bot: Bot, session: FakeSession) -> None:
        self.dp = dp
        self.bot = bot
        self.session = session
        self.unexpected: list[logging.LogRecord] = []
        self._update_ids = itertools.count(1)

    # ── Feeding updates ───────────────────────────────────────────────────────

    @staticmethod
    def _user(user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name="Tester")

    async def text(self, text: str, user_id: int) -> None:
        message = Message(
            message_id=next(self._update_ids),
            date=datetime.now(UTC),
            chat=Chat(id=user_id, type="private"),
            from_user=self._user(user_id),
            text=text,
        )
        await self.dp.feed_update(
            self.bot, Update(update_id=next(self._update_ids), message=message)
        )

    async def non_text(self, user_id: int) -> None:
        """Send a message without text (a photo), as a user might during a text prompt."""
        message = Message(
            message_id=next(self._update_ids),
            date=datetime.now(UTC),
            chat=Chat(id=user_id, type="private"),
            from_user=self._user(user_id),
            photo=[PhotoSize(file_id="f", file_unique_id="u", width=1, height=1)],
        )
        await self.dp.feed_update(
            self.bot, Update(update_id=next(self._update_ids), message=message)
        )

    async def press(self, data: str, user_id: int, message_id: int = 500) -> None:
        origin = Message(
            message_id=message_id,
            date=datetime.now(UTC),
            chat=Chat(id=user_id, type="private"),
            from_user=User(id=BOT_ID, is_bot=True, first_name="Bot"),
            text="previous screen",
        )
        callback = CallbackQuery(
            id=str(next(self._update_ids)),
            from_user=self._user(user_id),
            chat_instance="test",
            data=data,
            message=origin,
        )
        await self.dp.feed_update(
            self.bot, Update(update_id=next(self._update_ids), callback_query=callback)
        )

    # ── Inspecting what the bot did ───────────────────────────────────────────

    def reset(self) -> None:
        self.session.calls.clear()

    def _outgoing(self) -> list[TelegramMethod[Any]]:
        kinds = (SendMessage, EditMessageText, SendPhoto)
        return [c for c in self.session.calls if isinstance(c, kinds)]

    @property
    def last(self) -> TelegramMethod[Any]:
        outgoing = self._outgoing()
        assert outgoing, "the bot sent nothing"
        return outgoing[-1]

    @property
    def last_text(self) -> str:
        call = self.last
        return str(call.caption if isinstance(call, SendPhoto) else call.text)  # type: ignore[attr-defined]

    @property
    def last_buttons(self) -> list[str]:
        """Callback data (or url) of every button in the last message's keyboard."""
        markup = self.last.reply_markup  # type: ignore[attr-defined]
        if markup is None:
            return []
        return [b.callback_data or b.url or "" for row in markup.inline_keyboard for b in row]

    @property
    def alerts(self) -> list[str]:
        return [
            str(c.text) for c in self.session.calls if isinstance(c, AnswerCallbackQuery) and c.text
        ]

    @property
    def sent(self) -> list[SendMessage]:
        return [c for c in self.session.calls if isinstance(c, SendMessage)]

    @property
    def edits(self) -> list[EditMessageText]:
        return [c for c in self.session.calls if isinstance(c, EditMessageText)]

    @property
    def photos(self) -> list[SendPhoto]:
        return [c for c in self.session.calls if isinstance(c, SendPhoto)]


class _ErrorCollector(logging.Handler):
    def __init__(self, sink: list[logging.LogRecord]) -> None:
        super().__init__(level=logging.ERROR)
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self._sink.append(record)


def make_harness(dp: Dispatcher) -> tuple[Harness, logging.Handler]:
    session = FakeSession()
    bot = Bot(
        token=f"{BOT_ID}:TEST",
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    harness = Harness(dp, bot, session)
    collector = _ErrorCollector(harness.unexpected)
    logging.getLogger("handlers.errors").addHandler(collector)
    return harness, collector
