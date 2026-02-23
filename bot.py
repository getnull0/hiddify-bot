import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config import BOT_TOKEN
from handlers import common, users, server, account
from api.hiddify import close_session
from middlewares.throttle import ThrottleMiddleware

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
# Наш логгер — INFO, всё остальное (aiogram) — только WARNING+
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Глобальный обработчик ошибок
    @dp.errors()
    async def error_handler(event: ErrorEvent):
        log.exception("Unhandled error: %s", event.exception, exc_info=event.exception)
        if event.update.callback_query:
            cb = event.update.callback_query
            try:
                await cb.answer("❌ Ошибка сервера, попробуй позже", show_alert=True)
            except Exception:
                pass
        elif event.update.message:
            try:
                await event.update.message.answer("❌ Ошибка сервера, попробуй позже")
            except Exception:
                pass

    dp.message.middleware(ThrottleMiddleware(rate=1.0))
    dp.callback_query.middleware(ThrottleMiddleware(rate=1.0))

    dp.include_router(common.router)
    dp.include_router(users.router)
    dp.include_router(server.router)
    dp.include_router(account.router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть панель управления"),
    ])

    log.info("▶ Bot started (@%s)", (await bot.get_me()).username)
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_session()
        await bot.session.close()
        log.info("⏹ Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
