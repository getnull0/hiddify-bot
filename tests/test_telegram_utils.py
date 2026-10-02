from types import SimpleNamespace
from typing import Any, cast

import pytest
from aiogram.types import CallbackQuery, Message

from hiddify_bot.utils.telegram import (
    MissingEventDataError,
    callback_arg,
    data_of,
    message_of,
    text_of,
    user_id_of,
)


def _cb(**kw: Any) -> CallbackQuery:
    return cast(CallbackQuery, SimpleNamespace(**kw))


def _msg(**kw: Any) -> Message:
    return cast(Message, SimpleNamespace(**kw))


def test_data_of_returns_payload():
    assert data_of(_cb(data="user:abc")) == "user:abc"


def test_data_of_raises_without_data():
    with pytest.raises(MissingEventDataError):
        data_of(_cb(data=None))


def test_callback_arg_splits_on_first_colon_only():
    assert callback_arg(_cb(data="user_extend:abc:30")) == "abc:30"


def test_text_of_strips():
    assert text_of(_msg(text="  hi  ")) == "hi"


def test_text_of_non_text_message_is_empty():
    assert text_of(_msg(text=None)) == ""


def test_user_id_of_returns_sender_id():
    assert user_id_of(_cb(from_user=SimpleNamespace(id=42))) == 42


def test_user_id_of_raises_without_sender():
    with pytest.raises(MissingEventDataError):
        user_id_of(_cb(from_user=None))


def test_message_of_rejects_missing_message():
    with pytest.raises(MissingEventDataError):
        message_of(_cb(message=None))
