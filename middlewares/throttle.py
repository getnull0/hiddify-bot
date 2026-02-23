from collections import defaultdict
from time import monotonic
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 2.0):
        self.rate = rate
        self._last: dict[int, float] = defaultdict(float)

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user_id = data["event_from_user"].id
        now = monotonic()
        if now - self._last[user_id] < self.rate:
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро", show_alert=False)
            return
        self._last[user_id] = now
        return await handler(event, data)
