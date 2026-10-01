"""The shipped .env.example must stay in sync with what the settings loader requires."""

from pathlib import Path

from dotenv import dotenv_values

from config import _REQUIRED, Settings

EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"


def test_example_lists_every_required_variable():
    assert set(_REQUIRED) <= set(dotenv_values(EXAMPLE))


def test_example_is_a_loadable_configuration():
    values = {k: v or "" for k, v in dotenv_values(EXAMPLE).items()}
    settings = Settings.from_env(values)
    assert settings.verify_ssl is True
    assert settings.admin_ids
