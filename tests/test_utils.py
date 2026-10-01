from formatters import texts
from utils.html import esc, esc_tail
from utils.qr import qr_url
from utils.user_state import is_blocked, limit_gb, user_status


class TestEscTail:
    def test_short_text_is_only_escaped(self):
        assert esc_tail("a<b", 100) == "a&lt;b"

    def test_long_text_keeps_the_tail(self):
        result = esc_tail("0123456789", 5)
        assert result == "…6789"

    def test_result_never_exceeds_the_limit_after_escaping(self):
        text = "<&>" * 1000
        result = esc_tail(text, 200)
        assert len(result) <= 200
        assert result.startswith("…")
        assert result.endswith("&gt;")

    def test_tiny_limit_degrades_to_an_ellipsis(self):
        assert esc_tail("abcdef", 1) == "…"

    def test_empty_text(self):
        assert esc_tail("", 10) == ""


def test_esc_handles_falsy_and_non_strings():
    assert esc(None) == ""
    assert esc(0) == ""
    assert esc(5) == "5"
    assert esc("<b>") == "&lt;b&gt;"


def test_qr_url_encodes_the_payload():
    url = qr_url("https://h/x?a=b&c=d")
    assert url.startswith("https://api.qrserver.com/v1/create-qr-code/?size=300x300")
    assert url.endswith("data=https%3A%2F%2Fh%2Fx%3Fa%3Db%26c%3Dd")


class TestUserState:
    def test_limit_defaults_to_zero(self):
        assert limit_gb({}) == 0.0
        assert limit_gb({"usage_limit_GB": None}) == 0.0
        assert limit_gb({"usage_limit_GB": "12.5"}) == 12.5

    def test_blocked_when_disabled(self):
        assert is_blocked({"enable": False, "usage_limit_GB": 10})

    def test_blocked_when_limit_is_zero(self):
        assert is_blocked({"enable": True, "usage_limit_GB": 0})

    def test_enabled_with_limit_is_not_blocked(self):
        assert not is_blocked({"enable": True, "usage_limit_GB": 10})
        assert not is_blocked({"usage_limit_GB": 10})  # enable missing means enabled

    def test_status_classification(self):
        assert user_status({"enable": False, "usage_limit_GB": 10}) == "blocked"
        assert user_status({"usage_limit_GB": 10, "is_active": True}) == "active"
        assert user_status({"usage_limit_GB": 10, "is_active": False}) == "inactive"
        assert user_status({"usage_limit_GB": 10}) == "inactive"


def test_texts_escape_the_subscription_url():
    assert "&lt;x&gt;" in texts.link("<x>")
    assert "&lt;x&gt;" in texts.qr_caption("<x>", "Title")
    assert "<b>Title</b>" in texts.qr_caption("u", "Title")
