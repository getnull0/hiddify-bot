# Architecture

```
hiddify_bot/             the application (run with: python -m hiddify_bot)
  __main__.py            entry point
  app.py                 create_dispatcher() (middleware + routers), startup check, main() polling loop
  config.py              Settings.from_env(): validation; module-level aliases for call sites
  api/client.py          HiddifyClient: one aiohttp session, errors, users cache, every panel call
  api/__init__.py        get_client() / set_client() / close_client(): the process-wide client
  services/              business logic over the client (user, account, server)
  handlers/              aiogram routers: common, account, server, users/ (package), errors
    users/               browse.py, actions.py (one-tap), wizards.py, views.py (card rendering), states.py
  keyboards/             inline keyboard builders; nav.py has the shared Back/Home/Close and pagination rows
  formatters/            pure functions turning panel dicts into HTML; texts.py holds shared messages
  filters/               IsAdmin
  middlewares/           ThrottleMiddleware (per-user rate limit)
  utils/                 html, telegram (typed event accessors), validation, user_state, qr, types
scripts/                 smoke.py (check your own panel), check_comments.py (CI gate)
tests/                   fakes/ (fake Hiddify panel + fake Telegram), unit and end-to-end tests
docs/                    this documentation
```

Everything the bot imports lives under `hiddify_bot/`; the repository root only carries tooling, docs and tests.

Control flow: Telegram update -> ThrottleMiddleware -> router (IsAdmin where needed) -> handler -> service -> `HiddifyClient` -> panel. Errors anywhere land in `handlers/errors.py`.

## Design decisions

- **Users cache.** `HiddifyClient` caches the users list for 30 s. `_request` invalidates it after every successful non-GET call under `/admin/user`, so new mutation methods are covered automatically.
- **Blocking.** Block is `enable=False`, unblock is `enable=True`. Users blocked by older versions (limit 0, still enabled) are recognised by `utils/user_state.is_blocked`; unblocking them asks for a new limit first.
- **Telegram event access.** Handlers use `utils/telegram` (`message_of`, `callback_arg`, `data_of`, `text_of`, `user_id_of`) instead of touching optional fields, which keeps mypy strict happy and makes non-text messages in a wizard step harmless.
- **Errors.** Handlers do not catch API errors. `handlers/errors.py` shows them as an alert (buttons) or a message (text) and keeps FSM state so the admin can retry. "message is not modified" is ignored. Callback handlers call `cb.answer()` after the work succeeds so a failure can still use the alert.
- **Pagination.** `users_list:{page}` stores `list_page` in FSM data; `views.edit_card` / `reply_card` pass it on so Back returns to the right page.
- **HTML.** Everything from the API or the user goes through `utils/html.esc`; text that must fit Telegram's 4096 characters uses `esc_tail`.
- **Routers** are module singletons that attach to one dispatcher only, so the dispatcher is built once (`create_dispatcher()`); tests share a session-scoped one.

## Conventions

- Callback data is colon-separated: `user:{uuid}`, `users_list:{page}`, `user_block|user_unblock|user_reset:{uuid}`, `user_extend:{uuid}:{days}`, `user_mode:{uuid}:{mode}`, `user_set_limit|user_set_days|user_set_mode|user_set_tgid:{uuid}`, `user_delete_confirm:{uuid}`, `user_delete:{uuid}` (matched with `^user_delete:[^_]`), `fsm_cancel:{back_cb}`, `fsm_back`, `logs:{filename}`, plus fixed strings such as `menu`, `user_menu`, `close`, `noop`.
- Every screen ends with `nav_row(...)`. Admin home is `menu`, user home is `user_menu`.
- Bot-facing text is Russian, parse mode HTML. `/start` is the only published command; it opens the user menu for everyone, with an extra "Админ-панель" button for admins (`/admin` also works, unlisted).
- Wizard input goes through `utils/validation` (finite numbers, panel limits). `.` skips an optional step in the create wizard.

## Tests

`tests/__init__.py` pins the environment. `tests/fakes/panel.py` is an in-process fake of the panel with the real semantics (404 on empty list, the `is_active` rule, JSON errors); `tests/fakes/telegram.py` records Bot API calls and feeds real updates through the real dispatcher. Real network is blocked in tests and warnings are errors.
