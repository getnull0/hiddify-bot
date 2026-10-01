"""Shared fixtures: a fake Hiddify panel, a real client against it, and a fake Telegram."""

import logging
from collections.abc import AsyncIterator

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import api
from api.client import HiddifyClient
from bot import create_dispatcher
from config import ADMIN_IDS, Settings
from tests.fakes.panel import ADMIN_UUID, PROXY_PATH, FakePanel
from tests.fakes.telegram import Harness, make_harness

ADMIN_ID = min(ADMIN_IDS)
MEMBER_ID = 2002
STRANGER_ID = 3003


def make_settings(base_url: str, **overrides: str) -> Settings:
    env = {
        "BOT_TOKEN": "42:TEST",
        "HIDDIFY_URL": base_url,
        "HIDDIFY_PROXY_PATH": PROXY_PATH,
        "HIDDIFY_USER_PATH": "userpath",
        "HIDDIFY_ADMIN_UUID": ADMIN_UUID,
        "ADMIN_IDS": str(ADMIN_ID),
    }
    env.update(overrides)
    return Settings.from_env(env)


@pytest.fixture
async def panel() -> AsyncIterator[FakePanel]:
    fake = FakePanel()
    await fake.start()
    yield fake
    await fake.stop()


@pytest.fixture
async def client(panel: FakePanel) -> AsyncIterator[HiddifyClient]:
    instance = HiddifyClient(make_settings(panel.base_url))
    api.set_client(instance)
    yield instance
    await instance.close()
    api.set_client(None)


@pytest.fixture(scope="session")
def dispatcher() -> Dispatcher:
    """Routers are module singletons and attach to one dispatcher only, so build it once."""
    return create_dispatcher(throttle_rate=0.0)


@pytest.fixture
async def bot(client: HiddifyClient, dispatcher: Dispatcher) -> AsyncIterator[Harness]:
    dispatcher.fsm.storage = MemoryStorage()  # fresh conversation state for every test
    harness, collector = make_harness(dispatcher)
    yield harness
    logging.getLogger("handlers.errors").removeHandler(collector)
    assert not harness.unexpected, [r.getMessage() for r in harness.unexpected]
