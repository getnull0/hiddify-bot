"""Application wiring: dispatcher assembly, startup panel check, and the polling lifecycle."""

import logging
from unittest.mock import AsyncMock

import bot as bot_main
from api.client import HiddifyClient
from tests.fakes.panel import FakePanel
from tests.fakes.telegram import make_harness


def test_dispatcher_has_every_router(dispatcher):
    assert len(dispatcher.sub_routers) == 5


async def test_check_panel_reports_success(client: HiddifyClient, caplog):
    with caplog.at_level(logging.INFO, logger="bot"):
        await bot_main.check_panel()
    assert "Hiddify panel OK (admin: Owner, super_admin)" in caplog.text


async def test_check_panel_explains_bad_credentials(panel: FakePanel, caplog):
    import api
    from tests.conftest import make_settings

    bad = HiddifyClient(make_settings(panel.base_url, HIDDIFY_ADMIN_UUID="wrong"))
    api.set_client(bad)
    try:
        with caplog.at_level(logging.WARNING, logger="bot"):
            await bot_main.check_panel()
    finally:
        await bad.close()
        api.set_client(None)
    assert "HIDDIFY_ADMIN_UUID" in caplog.text


async def test_main_wires_everything_and_cleans_up(client: HiddifyClient, dispatcher, monkeypatch):
    harness, _ = make_harness(dispatcher)
    polling = AsyncMock()
    monkeypatch.setattr(bot_main, "Bot", lambda **_kwargs: harness.bot)
    monkeypatch.setattr(bot_main, "create_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(dispatcher, "start_polling", polling)

    await bot_main.main()

    polling.assert_awaited_once_with(harness.bot, skip_updates=True)
    commands = [c for c in harness.session.calls if type(c).__name__ == "SetMyCommands"]
    assert [cmd.command for cmd in commands[0].commands] == ["start"]
