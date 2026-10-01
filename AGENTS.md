# AGENTS.md

Telegram bot (aiogram 3.x) for managing a self-hosted [Hiddify](https://github.com/hiddify/Hiddify-Panel) VPN panel. Built for the home / small-group case: you run your own VPN server and hand out access to family and friends, all from Telegram. Two roles in one bot:

- **Admin** — user management (create, block/unblock, extend, set traffic and day limits, reset-mode), server monitoring, and panel logs.
- **End user** — a self-service "my account" view: remaining traffic and days, subscription link, QR code, and client-app download links.

Open-source; originally built by the author for personal use and published as a portfolio project.

## Owner preferences

- Respond in Russian. Keep code, identifiers, commit messages and technical terms in English.

## Commands

```bash
# Run locally (requires .env — see .env.example)
python bot.py

# Docker (production path)
docker compose up -d --build

# Install deps
pip install -r requirements.txt

# Dev install (includes ruff, pytest, pre-commit)
pip install -r requirements-dev.txt
pre-commit install

# Update locked deps (edit requirements*.in, then recompile on Python 3.12)
pip-compile --generate-hashes --strip-extras -o requirements.txt requirements.in
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements-dev.txt requirements-dev.in

# Run every CI gate locally (lint, types, dead code, security, comments, tests)
make check
```

Individual gates: `make lint | typecheck | deadcode | security | audit | comments | test`.

Python 3.12. CI runs on push/PR via `.github/workflows/ci.yml` (lint + test + Docker build).

## Required Environment

All in `.env` (loaded by `config.py` via python-dotenv). See `.env.example` for a template.

- `BOT_TOKEN` — Telegram bot token
- `HIDDIFY_URL` — base URL of the Hiddify panel (trailing slash stripped)
- `HIDDIFY_PROXY_PATH` — path segment before `/api/v2` (e.g. the proxy prefix)
- `HIDDIFY_USER_PATH` — path segment used to build per-user subscription URLs
- `HIDDIFY_ADMIN_UUID` — admin API key (sent as `Hiddify-API-Key` header)
- `ADMIN_IDS` — comma-separated Telegram user IDs allowed into the admin panel
- `ADMIN_USERNAME` — Telegram username for support contact (without @, optional)
- `HIDDIFY_VERIFY_SSL` — `"true"` to verify certs; absent/anything else disables SSL verification (default, for self-signed / sslip.io setups)
- `QR_API_URL` — QR-code image API endpoint (optional; default `https://api.qrserver.com/v1/create-qr-code/`). Override to self-host QR generation instead of using the public service.

`config.py` validates required vars at import time — missing vars raise `SystemExit` with a clear message listing which ones are missing.

## Architecture

### Layering

```
bot.py            → entrypoint: Bot + Dispatcher, router registration, error handler, throttle middleware
handlers/         → aiogram Routers, one per domain (common, users, server, account)
  ↳ FSM states, callback routing, message handling
services/         → business logic, thin wrappers over the API layer
api/hiddify.py    → HTTP client for Hiddify REST API (one shared aiohttp.ClientSession)
keyboards/        → InlineKeyboard builders + shared nav/pagination helpers in nav.py
formatters/       → pure functions turning API dicts into HTML strings (with escaping)
filters/admin.py  → IsAdmin filter (checks event.from_user.id against ADMIN_IDS)
middlewares/      → ThrottleMiddleware (rate limiting per user)
utils/            → html.py esc() HTML-escape helper; telegram.py typed accessors for optional event fields
                    (message_of, user_id_of, callback_arg, data_of, text_of); validation.py number parsers;
                    types.py JsonDict alias
scripts/          → check_comments.py: CI gate for comment language and length
tests/            → pytest tests (formatters, keyboards, nav, account_service, server formatters)
```

Control flow: Telegram update → ThrottleMiddleware → Router → IsAdmin filter (where applicable) → handler → service → `api/hiddify.py` → Hiddify panel REST API. Formatters render the response HTML; keyboards attach navigation.

### Routers (registered in `bot.py` in this order)

- `common` — `/start`, `/admin`, close/menu/noop callbacks. Both admin and regular users.
- `users` — admin-only user CRUD, search, multi-step create wizard. Filter applied at router level: `router.message.filter(IsAdmin())` / `router.callback_query.filter(IsAdmin())`.
- `server` — admin-only server status, logs, update usage, panel info.
- `account` — "my account" for both admins and end users. No router-level filter; admin-only callbacks use per-handler `IsAdmin()` filter.

### The Hiddify v11 workaround (critical)

Per-user `/user/*` endpoints (`me`, `short`, `all-configs`, `apps`) return 400 due to a bug in Hiddify v11 auth middleware. Everything is done through admin endpoints instead:

- `services/account_service.py` builds the subscription URL manually from `HIDDIFY_URL` + `HIDDIFY_USER_PATH` + user UUID rather than fetching it from a user-scoped endpoint.
- `find_user_by_telegram_id` scans the full admin user list client-side.

Do not switch to `/user/*` endpoints without confirming the Hiddify bug is fixed.

### Users cache

`api/hiddify.py` keeps a module-level `_users_cache` with a 30-second TTL (`CACHE_TTL`). **Every function that mutates a user (`create_user`, `update_user`, `delete_user`, `reset_user_traffic`, `extend_user`) must set `_users_cache = None` to invalidate it.** Forgetting this leaves stale list views for up to 30s.

### Blocking vs. disabling

"Block user" sets `usage_limit_GB=0` — it does **not** touch the `enable` flag. This is intentional: it preserves protocol/config assignments while cutting off traffic. Unblock = set a positive limit again. See `services/user_service.py` `block()` / `unblock()`.

### aiohttp session lifecycle

One `aiohttp.ClientSession` is created lazily in `api/hiddify.py` (via `async _get_session()` with a lock to prevent double-init) and reused for the process. All requests have a 30s total / 15s connect timeout (`_TIMEOUT`). `close_session()` is called in the `finally` block of `bot.py`'s `main()`. The SSL context is built once at import time based on `HIDDIFY_VERIFY_SSL`.

### Pagination position preservation

When a user navigates `users_list:{page} → user:{uuid} → action → back`, the page number is stored in FSM state (`list_page` key) and passed through `user_actions_kb(uuid, limit, list_page=N)` so the Back button returns to the correct page, not page 0. When adding new handlers that show `user_actions_kb`, read `list_page` from `state.get_data()` and pass it through.

### HTML escaping

`utils/html.py` provides `esc()` — it wraps `aiogram.utils.text_decorations.html_decoration.quote`, stringifies its input, and returns `""` for falsy values. Formatters import it as `_esc`; handlers import it as `esc`. Always run any value that comes from the API or user input (name, comment, uuid, expiry_date, log content, error text, subscription URL) through it before inserting it into an HTML message.

## Conventions

### Callback data format

Colon-separated prefixes, parsed by `cb.data.split(":")` or `.startswith(...)`:

- `user:{uuid}` — user detail card
- `users_list:{page}` — paginated list (0-indexed)
- `user_block:{uuid}`, `user_unblock:{uuid}`, `user_reset:{uuid}`
- `user_extend:{uuid}:{days}` — carries an integer arg
- `user_set_limit:{uuid}`, `user_set_days:{uuid}`, `user_set_mode:{uuid}`, `user_set_tgid:{uuid}`
- `user_mode:{uuid}:{mode}` — mode is `monthly|weekly|daily|no_reset`
- `user_delete_confirm:{uuid}`, `user_delete:{uuid}` — note the delete-do handler uses `F.data.regexp(r"^user_delete:[^_]")` to avoid matching `user_delete_confirm:`
- `fsm_cancel:{back_cb}`, `fsm_back` — FSM navigation
- `logs:{filename}` — filename is passed verbatim
- `close`, `menu`, `user_menu`, `noop`, `server_status`, `logs_menu`, etc. — fixed strings

### Navigation keyboards

`keyboards/nav.py` provides `nav_row(back_cb, home_cb)` and `pagination_row(...)`. Most keyboards end with `kb.row(*nav_row(...))` so every screen has consistent Back / Home / Close buttons. Admin home callback is `menu`; regular-user home is `user_menu`. When adding a keyboard, follow this pattern.

Photo messages (QR codes) use `photo_nav_kb(back_cb, home_cb)` for navigation.

### FSM wizards

Multi-step input uses `aiogram.fsm.state.StatesGroup`. Each state stores `uuid`, `field`, `back_cb`, and `list_page` in state data so the cancel button can return to the right screen and page. `fsm_nav_kb(back_cb, has_prev)` renders `[◀️ Назад] [❌ Отмена]`; `fsm_cancel_kb(back_cb)` for single-step wizards. The `.` input means "skip / use default" in create-user wizard.

### UI language

All bot-facing strings (commands, buttons, messages, error text) are in Russian. Only one command is published via `bot.set_my_commands` in `bot.py`: `/start`. `/admin` is an unlisted admin-only command (handled in `handlers/common.py` behind `IsAdmin()`), deliberately kept out of the Telegram command menu. Parse mode is `HTML` (`ParseMode.HTML`).

### Error handling

Global error handler in `bot.py` (`@dp.errors()`) logs the exception and answers the user with a generic "server error" message. API call failures inside handlers are caught and surfaced as `❌ Ошибка API: {e}`. The `close` callback handler catches `TelegramBadRequest` silently (message may already be deleted).

### Logs

Logging is set to `WARNING` globally except the bot's own logger (`bot`), which is `INFO`. `skip_updates=True` on polling means missed updates during downtime are not processed.

## Testing

Tests are in `tests/` and use pytest with `pytest-asyncio` (auto mode). Run with `make test`. Tests cover:

- `test_formatters.py` — `user_card`, `account_card` (including HTML escaping, missing fields, edge cases)
- `test_keyboards.py` — `nav_row`, `pagination_row`
- `test_inline_keyboards.py` — keyboard builders (`admin_main_kb`, `user_actions_kb`, `users_list_kb`, `photo_nav_kb`)
- `test_account_service.py` — `_sub_url`, `_days_left`, `_expiry_date` (date math, expiry, invalid-date handling)
- `test_server_formatters.py` — `server_status`, `panel_info` (nested/flat data, usage history, top-5, HTML escaping, zero-division guards)
- `test_telegram_utils.py`, `test_validation.py` — typed event accessors and number parsing (NaN/inf rejected)
- `test_check_comments.py` — the comment gate itself

Tests require env vars (config.py validates at import); `make test` sets dummy values. Without make: `BOT_TOKEN=test HIDDIFY_URL=http://test HIDDIFY_PROXY_PATH=test HIDDIFY_USER_PATH=test HIDDIFY_ADMIN_UUID=test ADMIN_IDS=123 pytest -v`

## Quality gates

CI (`.github/workflows/ci.yml`) runs these jobs in parallel; the final `gate` job fails if any of them fails and is the single check to require in branch protection.

| Job | Tool | What it enforces |
|-----|------|------------------|
| lint | ruff | style, imports, bugbear, bandit rules (`S`), complexity, no `print`, no commented-out code, no blind `except` |
| typecheck | mypy `--strict` | full type coverage; use `utils/telegram.py` helpers instead of `cb.message` / `msg.text` directly |
| quality | vulture, `scripts/check_comments.py` | no dead code; comments and docstrings in English, at most 2 lines |
| security | bandit, pip-audit | insecure patterns; known CVEs in locked dependencies |
| test | pytest + coverage | tests pass and coverage stays at or above `fail_under` in `pyproject.toml` (ratchet: only raise it) |
| build | docker | image builds from the hashed lock file |

Rules worth remembering:
- Comments and docstrings must be English, ASCII letters only (symbols and emoji are fine), max 2 lines per block. Bot-facing strings stay Russian; they are not comments.
- A new vulture false positive is fixed by using the code, not by whitelisting it. Handlers decorated with `@router.*` / `@dp.*` are already ignored.
- Dependencies: edit `requirements.in` / `requirements-dev.in`, then `make lock`. Never edit the `.txt` lock files by hand.
- Pre-commit runs ruff, mypy, vulture and the comment gate locally.

## Docker

- `Dockerfile` — Python 3.12-slim, runs as non-root user `botuser`
- `docker-compose.yml` — healthcheck, restart unless-stopped, env_file

## Gotchas

- **`.env` is gitignored.** See `.env.example` for the template.
- **`ADMIN_IDS` is a Python `set` of `int`** parsed from a comma-separated env var. Membership checks are `in ADMIN_IDS`.
- **`ADMIN_USERNAME` is optional** — if not set, the "contact admin" message says "обратись к администратору" without a username link.
- **Log view endpoint returns HTML, not JSON.** `services/server_service.py` `_strip_html()` removes tags; content is truncated to the last 3800 chars to fit Telegram message limits.
- **`get_logs` uses form-encoded POST** (drops `Content-Type: application/json` header) because the Hiddify endpoint expects form data.
- **`update_usage` endpoint returns text/html**, not JSON — `api/hiddify.py` does not call `.json()` on it.
- **`InlineKeyboardButton(style=...)`** — the `style` kwarg (`primary`/`success`/`danger`) is an aiogram 3.25+ feature for Telegram button styling; older aiogram versions will reject it.
- **QR codes** are generated via an external HTTP service (default `api.qrserver.com`, overridable with the `QR_API_URL` env var), not locally. The subscription URL is URL-encoded and passed as the `data` query param.
- **Subscription URL** is `{HIDDIFY_URL}/{HIDDIFY_USER_PATH}/{uuid}/` — built in `account_service._sub_url()`, not fetched from the API.
- **HTTP timeouts** — all API requests have 30s total / 15s connect timeout. If the Hiddify panel is unresponsive, the bot will fail with a timeout error rather than hanging indefinitely.
- **aiohttp session creation is async** — `_get_session()` is `async` and uses a lock (`_session_lock`) to prevent double-init under concurrent requests. All callers must `await _get_session()`.
