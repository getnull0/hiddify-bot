"""Hiddify panel API access: one shared client per process."""

from hiddify_bot.api.client import HiddifyClient
from hiddify_bot.config import settings

__all__ = ["close_client", "get_client", "set_client"]

_client: HiddifyClient | None = None


def get_client() -> HiddifyClient:
    """Return the process-wide client, creating it on first use."""
    global _client
    if _client is None:
        _client = HiddifyClient(settings)
    return _client


def set_client(client: HiddifyClient | None) -> None:
    """Replace the shared client (used by tests)."""
    global _client
    _client = client


async def close_client() -> None:
    if _client is not None:
        await _client.close()
