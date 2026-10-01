# AGENTS.md

Telegram bot (aiogram 3.x) for managing a self-hosted [Hiddify](https://github.com/hiddify/Hiddify-Panel) VPN panel. Built for the home / small-group case: you run your own VPN server and hand out access to family and friends, all from Telegram. Two roles in one bot:

- **Admin**: user management (create, block/unblock, extend, limits, reset mode), server monitoring, panel logs.
- **End user**: self-service "my account": remaining traffic and days, subscription link, QR code, client-app links.

## Owner preferences

- Respond in Russian. Keep code, identifiers, commit messages and technical terms in English.

## Commands

```bash
python bot.py                    # run locally (needs .env, see .env.example)
docker compose up -d --build     # production path
pip install -r requirements-dev.txt && pre-commit install

make check                       # every CI gate locally
make lock                        # recompile requirements*.txt after editing the *.in files
```

Individual gates: `make lint | typecheck | deadcode | security | audit | comments | test`. Python 3.12.

## Environment

All in `.env` (loaded by `config.py`, validated into a frozen `Settings` dataclass; a bad value exits with a readable message). `.env.example` documents each variable and is covered by a test.

- `BOT_TOKEN`: Telegram bot token.
- `ADMIN_IDS`: comma-separated Telegram ids allowed into the admin panel.
- `HIDDIFY_URL`: panel base URL (must include http/https; trailing slash stripped).
- `HIDDIFY_PROXY_PATH`: the **admin** proxy path (first segment of the admin link).
- `HIDDIFY_ADMIN_UUID`: admin UUID, sent as the `Hiddify-API-Key` header.
- `HIDDIFY_USER_PATH`: the **client** proxy path, used to build subscription links.
- `HIDDIFY_VERIFY_SSL`: `true` verifies TLS; anything else skips verification (self-signed / sslip.io).
- `ADMIN_USERNAME` (optional): support contact shown to unknown users.
- `QR_API_URL` (optional): QR image service; override to self-host.

## Architecture

```
bot.py            entrypoint: create_dispatcher() (middleware + routers) and main() (polling)
config.py         Settings.from_env(): validation; module-level aliases for call sites
api/client.py     HiddifyClient: one aiohttp session, errors, users cache, every panel call
api/__init__.py   get_client() / set_client() / close_client(): the process-wide client
services/         business logic over the client (user, account, server)
handlers/         aiogram routers: common, account, server, users/ (package), errors
  users/          browse.py (list, card, search, link/qr/apps), actions.py (one-tap),
                  wizards.py (create/edit/tg id/unblock), views.py (card rendering), states.py
keyboards/        inline keyboard builders; nav.py has the shared Back/Home/Close and pagination rows
formatters/       pure functions turning panel dicts into HTML; texts.py holds shared messages
filters/admin.py  IsAdmin
middlewares/      ThrottleMiddleware (per-user rate limit)
utils/            html (esc, esc_tail), telegram (typed event accessors), validation,
                  user_state (blocked/active classification), qr, types (JsonDict)
scripts/          check_comments.py: CI gate for comment language and length
tests/            fakes/ (fake Hiddify panel + fake Telegram), unit and end-to-end tests
```

Control flow: Telegram update -> ThrottleMiddleware -> router (IsAdmin where needed) -> handler -> service -> `HiddifyClient` -> panel. Errors anywhere land in `handlers/errors.py`.

### Panel API facts (verified against Hiddify-Panel v14.0.0b5 source)

- The panel decides the account type from the **proxy path in the URL**. Admin endpoints (`/<admin_path>/api/v2/admin/...`) need the admin UUID. The per-user endpoints (`/user/me/` etc.) live under the *client* path and need the *user's own* UUID, so they cannot be used with the admin key. That is why the bot reads everything via admin endpoints and builds the subscription link itself: `{HIDDIFY_URL}/{HIDDIFY_USER_PATH}/{uuid}/`.
- `GET /admin/user/` answers **404 "You have no user"** for an empty list. `HiddifyClient._fetch_users` turns that into `[]` after confirming credentials via `/admin/me/`.
- Errors are JSON `{"message": ..., "detail": ...}`; wrong key, wrong role or wrong path give 403/404. `HiddifyApiError.message` carries the panel's message.
- `is_active` is `enable and usage_limit >= usage and remaining_days >= 0`. **A zero limit does not block a user who has used nothing**, so blocking uses `enable=False` (the panel drops the client from the proxy cores immediately).
- `telegram_id` can be set but not cleared through the API (the panel ignores falsy values).
- `usage_limit_GB` is capped by the panel at 1,000,000. `start_date` stays `null` until the first connection.
- Dates: `start_date` is `YYYY-MM-DD`; `last_online` is `YYYY-MM-DD HH:MM:SS`, `0001-...` meaning never.
- `update_user_usage` and `log` need the super admin; `log` takes a form POST with `file` and returns an HTML page (with `<style>`), which `server_service` strips.

### Users cache

`HiddifyClient` caches the users list for 30 s (`CACHE_TTL`). `_request` invalidates it after **every** successful non-GET call under `/admin/user`, so new mutation methods get correct behavior for free. Do not clear the cache by hand.

### Blocking

Block = `enable=False`; unblock = `enable=True` (one tap). Users blocked by older bot versions (limit 0, still enabled) are recognised by `utils/user_state.is_blocked`; unblocking them asks for a new limit first.

### Telegram event access

Never touch `cb.message`, `cb.data`, `msg.text` or `from_user` directly: use `utils/telegram` (`message_of`, `callback_arg`, `data_of`, `text_of`, `user_id_of`). They satisfy mypy strict and make non-text messages in a wizard step harmless (`text_of` returns `""`).

### Errors

Handlers do not catch API errors. `handlers/errors.py` shows `HiddifyApiError` / aiohttp / timeout failures as an alert (buttons) or message (text) and keeps FSM state, so the admin can retry. "message is not modified" is ignored; anything else is logged and answered with a generic message. Callback handlers call `cb.answer()` *after* the work succeeds so a failure can still use the alert.

### Pagination position preservation

`users_list:{page}` stores `list_page` in FSM data; `views.edit_card` / `reply_card` pass it to `user_actions_kb` so Back returns to the right page.

### HTML escaping

`utils/html.esc` (aliased `_esc` in formatters) must wrap every API- or user-supplied value put into an HTML message. Use `esc_tail` for text that must fit Telegram's 4096-character limit.

## Conventions

### Callback data

Colon-separated, parsed with `callback_arg` / `data_of`:

- `user:{uuid}`, `users_list:{page}`, `user_block:{uuid}`, `user_unblock:{uuid}`, `user_reset:{uuid}`
- `user_extend:{uuid}:{days}`, `user_mode:{uuid}:{mode}` (`no_reset|monthly|weekly|daily`)
- `user_set_limit|user_set_days|user_set_mode|user_set_tgid:{uuid}`
- `user_delete_confirm:{uuid}`, `user_delete:{uuid}` (the delete handler uses `F.data.regexp(r"^user_delete:[^_]")`)
- `fsm_cancel:{back_cb}`, `fsm_back`, `logs:{filename}`
- fixed: `close`, `menu`, `user_menu`, `noop`, `server_status`, `logs_menu`, `update_usage`, `panel_info`, `my_account`, `my_link`, `my_qr`, `my_apps`, `admin_my_account`, `user_create`, `user_search`

### Keyboards

`keyboards/nav.py` provides `nav_row(back_cb, home_cb)` and `pagination_row`. End every screen with `kb.row(*nav_row(...))`. Admin home is `menu`, user home is `user_menu`. Photo messages use `photo_nav_kb`.

### Wizards

`handlers/users/wizards.py`. Each state stores `uuid`, `field`, `back_cb` and `list_page` where relevant. Input is parsed by `utils/validation` (finite numbers only, panel limits enforced). `.` skips an optional step in the create wizard.

### UI language

Bot-facing strings are Russian. `/start` is the only published command and opens the user menu for everyone, admins included (they use the bot as users too); admins open the panel with the unlisted `/admin`. Parse mode is HTML.

### Logging

Root level WARNING; the `bot` and `handlers` loggers are INFO. Polling uses `skip_updates=True`.

## Testing

`make test` (pytest, asyncio auto mode). `tests/__init__.py` pins the environment, so tests never depend on a developer's shell or `.env`.

- `tests/fakes/panel.py`: in-process aiohttp fake of the Hiddify v14 admin API with the real semantics (404 on empty list, `is_active` rule, JSON errors, 403 on a wrong key). Extend it when the real API behavior is learned.
- `tests/fakes/telegram.py`: `FakeSession` records every Bot API call; `Harness.text()` / `.press()` feed real updates through the real dispatcher, so a test exercises handler -> service -> client -> fake panel.
- Fixtures (`conftest.py`): `panel`, `client`, `bot` (the harness); the dispatcher is session-scoped because routers attach to one dispatcher only.
- A test that expects a handler crash must clear `bot.unexpected`; any other unexpected error fails the test at teardown.
- Search matches uuid fragments, so tests needing exact matches use fixed uuids.

## Quality gates

CI (`.github/workflows/ci.yml`) runs these jobs in parallel; the final `gate` job fails if any fails and is the single check to require in branch protection.

| Job | Tool | Enforces |
|-----|------|----------|
| lint | ruff | style, imports, bugbear, bandit rules (`S`), complexity, no `print`, no commented-out code, no blind `except` |
| typecheck | mypy `--strict` | full type coverage |
| quality | vulture, `scripts/check_comments.py` | no dead code; comments and docstrings in English, at most 2 lines |
| security | bandit, pip-audit | insecure patterns; known CVEs in locked dependencies |
| test | pytest + coverage | tests pass; coverage at or above `fail_under` (95; only raise it) |
| build | docker | image builds from the hashed lock file |

Rules worth remembering:
- Comments and docstrings: English, ASCII letters only (symbols and emoji are fine), max 2 lines per block. Bot-facing strings stay Russian; they are not comments.
- Fix a vulture finding by using or deleting the code. `set_client` is a deliberate test seam listed in `api.__all__`.
- Dependencies: edit `requirements.in` / `requirements-dev.in`, then `make lock`. Never edit the `.txt` lock files by hand.
- Pre-commit runs ruff, mypy, vulture and the comment gate locally.

## Docker

`Dockerfile`: Python 3.12-slim, hashed install, non-root `botuser`. `docker-compose.yml`: restart unless-stopped, `env_file: .env`.

## Gotchas

- `.gitignore` ignores `.env.*`; `.env.example` is re-included explicitly. Keep it that way.
- `ADMIN_IDS` is a frozenset of ints; check membership with `in ADMIN_IDS`.
- Routers are module singletons and can attach to one dispatcher; build it once (`create_dispatcher()`).
- `InlineKeyboardButton(style=...)` needs aiogram 3.25+.
- QR codes come from an external service (`QR_API_URL`); the subscription URL is URL-encoded into the `data` param.
- All panel requests time out after 30 s total / 15 s connect.
