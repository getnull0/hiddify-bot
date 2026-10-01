import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from api.hiddify import close_session
from config import BOT_TOKEN
from handlers import account, common, server, users
from middlewares.throttle import ThrottleMiddleware

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
# Our logger is INFO; everything else (aiogram) is WARNING and above
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Global error handler
    @dp.errors()
    async def error_handler(event: ErrorEvent) -> None:
        log.error("Unhandled error: %s", event.exception, exc_info=event.exception)
        if event.update.callback_query:
            cb = event.update.callback_query
            with contextlib.suppress(Exception):
                await cb.answer("❌ Ошибка сервера, попробуй позже", show_alert=True)
        elif event.update.message:
            with contextlib.suppress(Exception):
                await event.update.message.answer("❌ Ошибка сервера, попробуй позже")

    dp.message.middleware(ThrottleMiddleware(rate=1.0))
    dp.callback_query.middleware(ThrottleMiddleware(rate=1.0))

    dp.include_router(common.router)
    dp.include_router(users.router)
    dp.include_router(server.router)
    dp.include_router(account.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть панель управления"),
        ]
    )

    log.info("▶ Bot started (@%s)", (await bot.get_me()).username)
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_session()
        await bot.session.close()
        log.info("⏹ Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
