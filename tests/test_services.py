"""Service layer against the fake panel."""

import pytest

import services.account_service as account_svc
import services.server_service as server_svc
import services.user_service as svc
from tests.fakes.panel import FakePanel, started_ago


class TestUserService:
    async def test_block_disables_user(self, client, panel: FakePanel):
        user = panel.add_user()
        blocked = await svc.block(user["uuid"])
        assert blocked["enable"] is False
        assert blocked["is_active"] is False

    async def test_unblock_re_enables_without_touching_limit(self, client, panel: FakePanel):
        user = panel.add_user(enable=False, usage_limit_GB=20.0)
        result = await svc.unblock(user["uuid"])
        assert result["enable"] is True
        assert result["usage_limit_GB"] == 20.0

    async def test_unblock_with_new_limit(self, client, panel: FakePanel):
        user = panel.add_user(enable=True, usage_limit_GB=0.0)
        result = await svc.unblock(user["uuid"], 75.0)
        assert result["usage_limit_GB"] == 75.0

    async def test_create_get_update_delete(self, client, panel: FakePanel):
        created = await svc.create("Zed", 15, 12.5, 4242)
        assert (await svc.get(created["uuid"]))["telegram_id"] == 4242
        assert (await svc.update(created["uuid"], package_days=99))["package_days"] == 99
        await svc.delete(created["uuid"])
        assert await svc.get_all() == []

    async def test_reset_and_extend(self, client, panel: FakePanel):
        user = panel.add_user(current_usage_GB=10.0, package_days=30)
        assert (await svc.reset_traffic(user["uuid"]))["current_usage_GB"] == 0
        assert (await svc.extend(user["uuid"], 5))["package_days"] == 35

    async def test_find_by_tg_id(self, client, panel: FakePanel):
        panel.add_user(name="Tg", telegram_id=55)
        assert (await svc.find_by_tg_id(55))["name"] == "Tg"
        assert await svc.find_by_tg_id(56) is None


class TestSearch:
    @pytest.fixture(autouse=True)
    def _users(self, panel: FakePanel):
        # Fixed uuids: search also matches uuid fragments, so random ones could collide
        self.alice = panel.add_user(
            name="Alice Smith", telegram_id=1234, uuid="aaaaaaaa-0000-4000-8000-000000000001"
        )
        self.bob = panel.add_user(name="Bob", uuid="bbbbbbbb-0000-4000-8000-000000000002")

    async def test_by_name_is_case_insensitive_substring(self, client):
        assert [u["name"] for u in await svc.search("ALICE")] == ["Alice Smith"]

    async def test_by_uuid_fragment(self, client):
        found = await svc.search(self.bob["uuid"][:8])
        assert [u["name"] for u in found] == ["Bob"]

    async def test_by_exact_telegram_id(self, client):
        assert [u["name"] for u in await svc.search("1234")] == ["Alice Smith"]
        assert await svc.search("123") == []

    async def test_blank_query_matches_nothing(self, client):
        assert await svc.search("   ") == []

    async def test_user_without_name_is_safe(self, client, panel: FakePanel):
        panel.add_user(name=None)
        assert [u["name"] for u in await svc.search("bob")] == ["Bob"]


class TestServerService:
    async def test_status(self, client):
        assert (await server_svc.get_status())["stats"]["system"]["cpu_percent"] == 12.5

    async def test_update_usage(self, client, panel: FakePanel):
        await server_svc.update_usage()
        assert panel.count("GET", "/admin/update_user_usage/") == 1

    async def test_logs_are_stripped_of_markup_and_styles(self, client, panel: FakePanel):
        panel.logs["x.log"] = "a < b"
        text = await server_svc.get_logs("x.log")
        assert text == "a < b"
        assert "ansi2html" not in text

    async def test_empty_log(self, client, panel: FakePanel):
        panel.logs["empty.log"] = ""
        assert await server_svc.get_logs("empty.log") == "(пусто)"

    async def test_panel_info_combines_version_and_admin(self, client):
        assert await server_svc.get_panel_info() == {
            "version": "14.0.0b5",
            "admin_name": "Owner",
            "admin_mode": "super_admin",
        }


class TestAccountService:
    async def test_account_for_unstarted_user(self, client, panel: FakePanel):
        user = panel.add_user(name="Acc", package_days=30, current_usage_GB=5.0, mode="monthly")
        data = await account_svc.get_account(user["uuid"])
        assert data["name"] == "Acc"
        assert data["used"] == 5.0
        assert data["total"] == 50.0
        assert data["days_left"] == 30
        assert data["expiry_date"] is None
        assert data["last_online"] is None
        assert data["mode"] == "monthly"
        assert data["sub_url"].endswith(f"/userpath/{user['uuid']}/")

    async def test_account_for_started_user(self, client, panel: FakePanel):
        user = panel.add_user(
            package_days=30, start_date=started_ago(10), last_online="2026-01-02 03:04:05"
        )
        data = await account_svc.get_account(user["uuid"])
        assert data["days_left"] == 20
        assert data["expiry_date"] is not None
        assert data["last_online"] == "2026-01-02 03:04:05"
