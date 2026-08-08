"""Tests for services.account_service pure functions."""
from datetime import date, timedelta

from services.account_service import _days_left, _expiry_date, _sub_url


class TestSubUrl:
    def test_basic(self, monkeypatch):
        monkeypatch.setattr("services.account_service.HIDDIFY_URL", "https://panel.example.com")
        monkeypatch.setattr("services.account_service.HIDDIFY_USER_PATH", "sub")
        result = _sub_url("abc-123")
        assert result == "https://panel.example.com/sub/abc-123/"


class TestDaysLeft:
    def test_no_start_date(self):
        assert _days_left(None, 30) == 30

    def test_today_started(self):
        today = date.today().isoformat()
        result = _days_left(today, 30)
        assert result == 30

    def test_started_10_days_ago(self):
        start = (date.today() - timedelta(days=10)).isoformat()
        result = _days_left(start, 30)
        assert result == 20

    def test_expired(self):
        start = (date.today() - timedelta(days=40)).isoformat()
        result = _days_left(start, 30)
        assert result == 0

    def test_invalid_date(self):
        result = _days_left("not-a-date", 30)
        assert result == 30


class TestExpiryDate:
    def test_no_start_date(self):
        assert _expiry_date(None, 30) is None

    def test_valid_date(self):
        result = _expiry_date("2024-01-15", 30)
        assert result == "2024-02-14"

    def test_invalid_date(self):
        assert _expiry_date("not-a-date", 30) is None
