"""Tests for formatters.user — pure functions, no external deps needed."""

from formatters.user import account_card, user_card


class TestUserCard:
    def test_active_user(self):
        u = {
            "name": "Test User",
            "uuid": "abc-123",
            "current_usage_GB": 10.5,
            "usage_limit_GB": 50.0,
            "package_days": 30,
            "mode": "monthly",
            "is_active": True,
            "enable": True,
            "start_date": "2024-01-15",
            "last_online": "2024-06-01T12:00:00",
            "telegram_id": 123456789,
        }
        result = user_card(u)
        assert "Test User" in result
        assert "abc-123" in result
        assert "✅ Активен" in result
        assert "10.50 / 50.0 GB" in result
        assert "30 дн." in result
        assert "ежемесячно" in result
        assert "15.01.2024" in result
        assert "123456789" in result

    def test_blocked_user(self):
        u = {
            "name": "Blocked",
            "uuid": "xyz",
            "current_usage_GB": 0,
            "usage_limit_GB": 0,
            "package_days": 0,
            "mode": "no_reset",
            "is_active": False,
            "enable": True,
        }
        result = user_card(u)
        assert "⛔ Заблокирован" in result

    def test_disabled_user(self):
        u = {
            "name": "Disabled",
            "uuid": "xyz",
            "current_usage_GB": 5,
            "usage_limit_GB": 50,
            "package_days": 10,
            "mode": "no_reset",
            "is_active": False,
            "enable": False,
        }
        result = user_card(u)
        assert "⛔ Отключён" in result

    def test_html_escaping(self):
        u = {
            "name": "<script>alert('xss')</script>",
            "uuid": "abc",
            "current_usage_GB": 0,
            "usage_limit_GB": 50,
            "package_days": 30,
            "mode": "no_reset",
            "is_active": True,
            "enable": True,
            "comment": "<b>bold</b> & <i>italic</i>",
        }
        result = user_card(u)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "&lt;b&gt;bold&lt;/b&gt;" in result

    def test_missing_fields(self):
        u = {}
        result = user_card(u)
        assert "—" in result
        assert "0.00 / 0.0 GB" in result

    def test_never_online(self):
        u = {
            "name": "Test",
            "uuid": "abc",
            "current_usage_GB": 0,
            "usage_limit_GB": 50,
            "package_days": 30,
            "mode": "no_reset",
            "is_active": True,
            "enable": True,
            "last_online": "0001-01-01T00:00:00",
        }
        result = user_card(u)
        assert "никогда" in result

    def test_null_last_online(self):
        u = {
            "name": "Test",
            "uuid": "abc",
            "current_usage_GB": 0,
            "usage_limit_GB": 50,
            "package_days": 30,
            "mode": "no_reset",
            "is_active": True,
            "enable": True,
            "last_online": None,
        }
        result = user_card(u)
        assert "никогда" in result


class TestAccountCard:
    def test_basic(self):
        data = {
            "name": "Test User",
            "used": 15.5,
            "total": 50.0,
            "days_left": 20,
            "expiry_date": "2024-02-15",
            "last_online": "2024-06-01T12:00:00",
            "mode": "monthly",
        }
        result = account_card(data)
        assert "Test User" in result
        assert "15.50 / 50.0 GB" in result
        assert "20 дн." in result
        assert "ежемесячно" in result
        assert "2024-02-15" in result

    def test_expired(self):
        data = {
            "name": "Expired",
            "used": 50.0,
            "total": 50.0,
            "days_left": 0,
            "expiry_date": "2024-01-01",
            "mode": "no_reset",
            "last_online": None,
        }
        result = account_card(data)
        assert "истёк" in result

    def test_expiring_soon(self):
        data = {
            "name": "Expiring",
            "used": 45.0,
            "total": 50.0,
            "days_left": 2,
            "expiry_date": "2024-02-01",
            "mode": "daily",
            "last_online": None,
        }
        result = account_card(data)
        assert "скоро истечёт" in result

    def test_html_escaping(self):
        data = {
            "name": "<script>alert(1)</script>",
            "used": 0,
            "total": 50.0,
            "days_left": 30,
            "expiry_date": "2024-02-15",
            "mode": "no_reset",
            "last_online": None,
        }
        result = account_card(data)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_zero_total_no_division_error(self):
        data = {
            "name": "Test",
            "used": 0,
            "total": 0,
            "days_left": 30,
            "expiry_date": None,
            "mode": "no_reset",
            "last_online": None,
        }
        result = account_card(data)
        assert "0%" in result
