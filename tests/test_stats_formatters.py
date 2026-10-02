from hiddify_bot.formatters.stats import nodes_text, size, sparkline, stats_card
from hiddify_bot.formatters.user import account_card
from tests.fakes.panel import ADMIN_UUID, default_dashboard, node_row


class TestSize:
    def test_units(self):
        assert size(0) == "0 KB"
        assert size(2048) == "2 KB"
        assert size(5 * 1024**2) == "5.0 MB"
        assert size(3 * 1024**3) == "3.00 GB"


class TestSparkline:
    def test_scales_to_the_largest_value(self):
        assert sparkline([0, 4, 8]) == "▁▅█"

    def test_all_zero_is_flat(self):
        assert sparkline([0, 0, 0]) == "▁▁▁"

    def test_empty(self):
        assert sparkline([]) == ""


class TestStatsCard:
    def test_full_dashboard(self):
        card = stats_card(default_dashboard())
        assert "Пользователей: <b>12</b> (включено 10)" in card
        assert "сейчас <b>2</b>" in card
        assert "Сегодня: <b>2.00 GB</b> ▲100%" in card
        assert "7 дней: <b>9.00 GB</b> ▲12%" in card
        assert "30 дней: <b>40.00 GB</b> ▼20%" in card
        assert "Пик: 3.00 GB (2026-09-30)" in card
        assert "последние 30 дн." in card
        assert "<code>" in card

    def test_unknown_trend_is_omitted(self):
        data = default_dashboard()
        data["usage"]["trends"] = {"day": None, "week": None, "month": None}
        assert "▲" not in stats_card(data)
        assert "▼" not in stats_card(data)

    def test_empty_payload_does_not_crash(self):
        card = stats_card({})
        assert "Пользователей: <b>0</b>" in card
        assert "<code>" not in card

    def test_peak_date_is_escaped(self):
        data = default_dashboard()
        data["usage"]["peak"] = {"date": "<x>", "usage": 1}
        assert "&lt;x&gt;" in stats_card(data)


class TestNodesText:
    def test_lists_nodes_with_status_icons(self):
        text = nodes_text([node_row(1), node_row(2, status="offline"), node_row(3, status="never")])
        assert "Серверы (узлы)</b>: 3" in text
        assert "🟢 <b>node-1</b>" in text
        assert "🔴 <b>node-2</b>" in text
        assert "⚪ <b>node-3</b>" in text
        assert "сегодня: 1.00 GB, онлайн 3" in text
        assert "домены: node1.example.com" in text

    def test_never_leaks_the_admin_link(self):
        text = nodes_text([node_row(1)])
        assert ADMIN_UUID not in text
        assert "admin_url" not in text
        assert "/path/" not in text

    def test_names_are_escaped(self):
        assert "&lt;b&gt;" in nodes_text([node_row(1, name="<b>")])

    def test_node_without_details_or_host(self):
        text = nodes_text([{"id": 1, "name": "bare", "status": "late"}])
        assert "🟡 <b>bare</b> · —" in text


ACCOUNT = {"name": "A", "used": 1, "total": 10, "days_left": 5, "mode": "monthly"}


class TestAccountResetLine:
    def test_reset_days_are_shown(self):
        assert "ежемесячно, через 12 дн." in account_card({**ACCOUNT, "reset_days": 12})

    def test_without_reset_days(self):
        card = account_card({**ACCOUNT, "reset_days": None})
        assert "через" not in card
        assert "ежемесячно" in card
