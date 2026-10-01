import pytest

from utils.validation import parse_finite_float, parse_int


@pytest.mark.parametrize(("raw", "expected"), [("10", 10.0), ("2.5", 2.5), ("-1", -1.0)])
def test_parse_finite_float_accepts_numbers(raw, expected):
    assert parse_finite_float(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "nan", "inf", "-inf", "1e999"])
def test_parse_finite_float_rejects_garbage_and_non_finite(raw):
    assert parse_finite_float(raw) is None


def test_parse_int():
    assert parse_int("30") == 30
    assert parse_int("3.5") is None
    assert parse_int("") is None
