"""Tests for formatters.server — pure functions, no external deps needed."""

from formatters.server import panel_info, server_status


class TestServerStatus:
    def test_basic(self):
        data = {
            "stats": {
                "system": {
                    "cpu_percent": 45.5,
                    "ram_used": 2.0,
                    "ram_total": 4.0,
                    "disk_used": 10.0,
                    "disk_total": 20.0,
                    "load_avg_1min": 0.5,
                    "load_avg_5min": 0.4,
                    "load_avg_15min": 0.3,
                    "total_connections": 10,
                    "total_unique_ips": 5,
                    "net_total_cumulative_GB": 100.5,
                },
            },
        }
        result = server_status(data)
        assert "Статус сервера" in result
        assert "45.5%" in result
        assert "2.00 / 4.00 GB" in result
        assert "10.00 / 20.00 GB" in result
        assert "100.5 GB" in result
        assert "10" in result
        assert "5" in result

    def test_flat_data(self):
        data = {
            "system": {
                "cpu_percent": 10.0,
                "ram_used": 1.0,
                "ram_total": 2.0,
                "disk_used": 5.0,
                "disk_total": 10.0,
                "load_avg_1min": 0.1,
                "load_avg_5min": 0.2,
                "load_avg_15min": 0.3,
                "total_connections": 1,
                "total_unique_ips": 1,
                "net_total_cumulative_GB": 5.0,
            },
        }
        result = server_status(data)
        assert "10.0%" in result

    def test_with_usage_history(self):
        data = {
            "system": {},
            "usage_history": {
                "total": {"users": 50, "usage": 1073741824, "online": 5},
                "today": {"usage": 536870912},
            },
        }
        result = server_status(data)
        assert "50" in result
        assert "1.00 GB" in result
        assert "0.50 GB" in result

    def test_with_cpu_top(self):
        data = {
            "system": {},
            "top5": {
                "cpu": [("node", 50.0), ("python3", 25.0)],
            },
        }
        result = server_status(data)
        assert "CPU топ-5" in result
        assert "node" in result
        assert "50.0%" in result
        assert "python3" in result

    def test_html_escaping_in_cpu_top(self):
        data = {
            "system": {},
            "top5": {
                "cpu": [("<script>alert(1)</script>", 50.0)],
            },
        }
        result = server_status(data)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_zero_ram_no_division_error(self):
        data = {
            "system": {
                "ram_used": 0,
                "ram_total": 0,
                "disk_used": 0,
                "disk_total": 0,
            },
        }
        result = server_status(data)
        assert "0%" in result

    def test_empty_data(self):
        result = server_status({})
        assert "Статус сервера" in result


class TestPanelInfo:
    def test_basic(self):
        data = {"version": "11.0.0", "admin_name": "admin", "admin_mode": "advanced"}
        result = panel_info(data)
        assert "11.0.0" in result
        assert "admin" in result
        assert "advanced" in result

    def test_html_escaping(self):
        data = {
            "version": "<script>alert(1)</script>",
            "admin_name": "<b>admin</b>",
            "admin_mode": "<i>mode</i>",
        }
        result = panel_info(data)
        assert "<script>" not in result
        assert "<b>admin</b>" not in result
        assert "&lt;script&gt;" in result
        assert "&lt;b&gt;admin&lt;/b&gt;" in result
