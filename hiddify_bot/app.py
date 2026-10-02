"""Application wiring: dispatcher assembly, startup panel check, and the polling loop."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from hiddify_bot.api import close_client, get_client
from hiddify_bot.api.client import API_ERRORS, describe_api_error
from hiddify_bot.config import BOT_TOKEN
from hiddify_bot.handlers import account, common, errors, server, users
from hiddify_bot.middlewares.throttle import ThrottleMiddleware

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
# Our logger is INFO; everything else (aiogram) is WARNING and above
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
logging.getLogger("hiddify_bot").setLevel(logging.INFO)


def create_dispatcher(throttle_rate: float = 1.0) -> Dispatcher:
    """Build the dispatcher with middleware and every router attached."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottleMiddleware(rate=throttle_rate))
    dp.callback_query.middleware(ThrottleMiddleware(rate=throttle_rate))
    dp.include_routers(common.router, users.router, server.router, account.router, errors.router)
    return dp


async def check_panel() -> None:
    """Log a clear hint at startup if the panel is unreachable or the credentials are wrong."""
    try:
        me = await get_client().get_me()
    except API_ERRORS as exc:
        log.warning("Hiddify panel check failed: %s", describe_api_error(exc))
    else:
        log.info("Hiddify panel OK (admin: %s, %s)", me.get("name"), me.get("mode"))


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher()
    try:
        await bot.set_my_commands(
            [BotCommand(command="start", description="Открыть панель управления")]
        )
        await check_panel()
        log.info("▶ Bot started (@%s)", (await bot.get_me()).username)
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_client()
        await bot.session.close()
        log.info("⏹ Bot stopped")
