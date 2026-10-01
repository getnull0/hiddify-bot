from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from utils.telegram import user_id_of


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return user_id_of(event) in ADMIN_IDS
