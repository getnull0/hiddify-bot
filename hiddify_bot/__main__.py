"""Entry point: python -m hiddify_bot."""

import asyncio

from hiddify_bot.app import main

if __name__ == "__main__":
    asyncio.run(main())
