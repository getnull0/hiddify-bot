# AGENTS.md

Telegram bot (aiogram 3, Python 3.12) that manages a self-hosted [Hiddify](https://github.com/hiddify/Hiddify-Panel) VPN panel: admin tools (users, traffic, server status, logs) plus a self-service account view for end users. Talks to the panel's admin REST API only.

## Setup

```bash
pip install -r requirements-dev.txt && pre-commit install
cp .env.example .env              # fill in your values; never commit .env
python bot.py                     # run locally
docker compose up -d --build      # production path
```

## Commands

```bash
make check       # every CI gate: lint, typecheck, deadcode, security, comments, test
make test        # pytest with coverage (fail_under in pyproject.toml)
make lock        # recompile requirements*.txt after editing the .in files
```

Run `make check` before every commit. A change is not done until it is green.

## Code style

- Python 3.12, fully typed (`mypy --strict`), ruff for lint and format (line length 100).
- Comments and docstrings: **English**, ASCII letters only, **at most 2 lines** per block. A script enforces this (`make comments`). Bot-facing strings stay **Russian**.
- Keep code idiomatic to its neighbours; no commented-out code, no `print`, no blind `except`.
- Escape everything from the panel or the user with `utils.html.esc` before putting it into an HTML message.
- In handlers use `utils.telegram` helpers (`message_of`, `callback_arg`, `text_of`, `user_id_of`) instead of touching optional aiogram fields.
- Do not catch panel errors in handlers; `handlers/errors.py` reports them.

## Testing

- Add or update tests with every behavior change. Handler tests feed real updates through the dispatcher against the fake panel and fake Telegram in `tests/fakes/` (see `tests/conftest.py` fixtures `panel`, `client`, `bot`).
- When the real panel's behavior is learned, encode it in `tests/fakes/panel.py` first, then fix the code.
- Tests must not use the network, depend on the shell or `.env`, or leave files behind; CI enforces all three.
- Never lower `fail_under`; only raise it. Do not skip or weaken a test to get green.

## Dependencies

Edit `requirements.in` or `requirements-dev.in`, then run `make lock`. Never edit the `.txt` lock files by hand. The runtime lock carries hashes and goes into the Docker image; dev tools never do.

## Git and PRs

- Commit messages in English, imperative, explaining why. Do not commit secrets, `.env`, or generated artifacts.
- `master` is protected: work on a branch and open a PR; the `gate` check must pass.
- Do not rewrite shared history or push to `master` directly.

## Boundaries

- Never touch the panel through user-scoped `/user/*` endpoints; see `docs/hiddify-api.md`.
- Do not block users with `usage_limit_GB=0`; blocking is `enable=False`.
- Do not add runtime dependencies without a strong reason; the bot is deliberately small.
- Ask before changing user-visible behavior (menus, texts, flows) beyond what was requested.

## More

- Architecture, conventions and design decisions: `docs/architecture.md`
- What the bot relies on in the panel API: `docs/hiddify-api.md`
- User-facing setup guide: `README.md`
