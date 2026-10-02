"""Admin-only user management: browsing, one-tap actions and input wizards."""

from aiogram import Router

from hiddify_bot.filters.admin import IsAdmin
from hiddify_bot.handlers.users import actions, browse, wizards

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())
# Wizards first: their cancel/back callbacks must win over the generic "user:" prefix match.
router.include_routers(wizards.router, actions.router, browse.router)
