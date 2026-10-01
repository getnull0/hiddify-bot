from collections import OrderedDict
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from utils.types import JsonDict

_MAX_ENTRIES = 5000


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 2.0) -> None:
        self.rate = rate
        self._last: OrderedDict[int, float] = OrderedDict()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, JsonDict], Awaitable[Any]],
        event: TelegramObject,
        data: JsonDict,
    ) -> Any:
        user_id = data["event_from_user"].id
        now = monotonic()
        if now - self._last.get(user_id, 0) < self.rate:
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро", show_alert=False)
            return None
        self._last[user_id] = now
        if len(self._last) > _MAX_ENTRIES:
            self._last.popitem(last=False)
        return await handler(event, data)
