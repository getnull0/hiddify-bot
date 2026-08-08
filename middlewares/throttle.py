from collections import OrderedDict
from time import monotonic

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery

_MAX_ENTRIES = 5000


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 2.0):
        self.rate = rate
        self._last: OrderedDict[int, float] = OrderedDict()

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user_id = data["event_from_user"].id
        now = monotonic()
        if now - self._last.get(user_id, 0) < self.rate:
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро", show_alert=False)
            return
        self._last[user_id] = now
        if len(self._last) > _MAX_ENTRIES:
            self._last.popitem(last=False)
        return await handler(event, data)
