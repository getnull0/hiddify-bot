# Contributing

Thanks for helping. The bot is small on purpose: a change should fit in one pull request and leave `make check` green.

## Setup

```bash
git clone https://github.com/getnull0/hiddify-bot.git && cd hiddify-bot
pip install -r requirements-dev.txt && pre-commit install
make check        # lint, types, dead code, security, comment rules, tests with coverage
```

Tests need no `.env` and no real panel: they run against an in-process fake panel and a fake Telegram (`tests/fakes/`).

## Making a change

1. Branch from `master`. `master` is protected: changes land through a pull request whose `gate` check passes.
2. Add or update tests with the change. Handler tests feed real updates through the dispatcher, so a test shows what a button press does end to end.
3. If you learn something new about the real panel's behavior, encode it in `tests/fakes/panel.py` first, then fix the code. To compare against the real thing, see [docs/real-panel-testing.md](../docs/real-panel-testing.md).
4. Run `make check` before pushing.

## Rules the checks enforce

- Fully typed code (`mypy --strict`), ruff for lint and format.
- Comments and docstrings in English, at most 2 lines per block; bot-facing text stays Russian.
- No dead code, no real network in tests, no files left behind by tests.
- Coverage may only go up (`fail_under` in `pyproject.toml`).

## Dependencies

Edit `requirements.in` or `requirements-dev.in` and run `make lock`. Never edit the `.txt` lock files by hand. Adding a runtime dependency needs a good reason.

## Where things live

[docs/architecture.md](../docs/architecture.md) describes the layout and design decisions, and [docs/hiddify-api.md](../docs/hiddify-api.md) lists what the bot relies on in the panel API. [AGENTS.md](../AGENTS.md) has the same rules in the form AI coding agents read.
