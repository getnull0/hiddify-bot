"""The real HTTP client against the fake panel."""

import json
from datetime import date, timedelta

import aiohttp
import pytest

from hiddify_bot.api import close_client, get_client, set_client
from hiddify_bot.api.client import API_ERRORS, HiddifyApiError, HiddifyClient, describe_api_error
from tests.conftest import make_settings
from tests.fakes.panel import ADMIN_UUID, FakePanel, node_row, started_ago


class TestUsersListAndCache:
    async def test_empty_panel_returns_empty_list(self, client: HiddifyClient, panel: FakePanel):
        assert await client.list_users() == []
        assert panel.count("GET", "/admin/me/") == 1

    async def test_returns_users(self, client: HiddifyClient, panel: FakePanel):
        panel.add_user(name="A")
        panel.add_user(name="B")
        assert {u["name"] for u in await client.list_users()} == {"A", "B"}

    async def test_list_is_cached(self, client: HiddifyClient, panel: FakePanel):
        panel.add_user()
        await client.list_users()
        await client.list_users()
        assert panel.count("GET", "/admin/user/") == 1

    async def test_mutation_invalidates_cache(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user(name="Old")
        await client.list_users()
        await client.update_user(user["uuid"], name="New")
        assert (await client.list_users())[0]["name"] == "New"
        assert panel.count("GET", "/admin/user/") == 2

    async def test_empty_list_with_bad_credentials_is_an_error(self, panel: FakePanel):
        bad = HiddifyClient(make_settings(panel.base_url, HIDDIFY_ADMIN_UUID="wrong"))
        try:
            with pytest.raises(HiddifyApiError) as exc:
                await bad.list_users()
            assert exc.value.status == 403
        finally:
            await bad.close()

    async def test_non_list_payload_is_rejected(self, client: HiddifyClient, panel: FakePanel):
        panel.respond_next('{"not": "a list"}', content_type="application/json")
        with pytest.raises(HiddifyApiError, match="формат"):
            await client.list_users()

    async def test_find_by_telegram_id(self, client: HiddifyClient, panel: FakePanel):
        panel.add_user(name="Linked", telegram_id=777)
        assert (await client.find_user_by_telegram_id(777))["name"] == "Linked"
        assert await client.find_user_by_telegram_id(1) is None


class TestUserMutations:
    async def test_create_user_sends_expected_payload(
        self, client: HiddifyClient, panel: FakePanel
    ):
        user = await client.create_user("Bob", days=10, limit_gb=5, mode="monthly", telegram_id=9)
        stored = panel.users[user["uuid"]]
        assert (stored["name"], stored["package_days"], stored["usage_limit_GB"]) == ("Bob", 10, 5)
        assert (stored["mode"], stored["telegram_id"], stored["enable"]) == ("monthly", 9, True)

    async def test_create_user_without_telegram_id(self, client: HiddifyClient, panel: FakePanel):
        user = await client.create_user("Eve")
        assert panel.users[user["uuid"]]["telegram_id"] is None

    async def test_create_user_validation_error_is_readable(self, client: HiddifyClient):
        with pytest.raises(HiddifyApiError) as exc:
            await client.create_user("Bad", mode="nonsense")
        assert exc.value.status == 422
        assert "Validation error" in exc.value.message
        assert "mode" in exc.value.message

    async def test_update_and_get(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user()
        updated = await client.update_user(user["uuid"], usage_limit_GB=99)
        assert updated["usage_limit_GB"] == 99
        assert (await client.get_user(user["uuid"]))["usage_limit_GB"] == 99

    async def test_delete(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user()
        assert (await client.delete_user(user["uuid"]))["msg"] == "ok"
        with pytest.raises(HiddifyApiError) as exc:
            await client.get_user(user["uuid"])
        assert exc.value.status == 404

    async def test_reset_traffic(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user(current_usage_GB=40.0)
        assert (await client.reset_user_traffic(user["uuid"]))["current_usage_GB"] == 0

    async def test_user_path_is_quoted(self, client: HiddifyClient):
        with pytest.raises(HiddifyApiError):
            await client.get_user("../admin/me")


class TestExtend:
    async def test_not_started_adds_to_package(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user(package_days=30)
        assert (await client.extend_user(user["uuid"], 30))["package_days"] == 60

    async def test_started_package_adds_days(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user(package_days=30, start_date=started_ago(10))
        assert (await client.extend_user(user["uuid"], 30))["package_days"] == 60

    async def test_expired_package_is_revived(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user(package_days=30, start_date=started_ago(100))
        assert user["is_active"] is False
        result = await client.extend_user(user["uuid"], 30)
        assert result["package_days"] == 130
        assert result["is_active"] is True
        remaining = (
            result["package_days"] - (date.today() - date.fromisoformat(result["start_date"])).days
        )
        assert remaining == 30

    async def test_bad_start_date_is_ignored(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user(package_days=30)
        panel.respond_next(
            json.dumps({**user, "start_date": "garbage"}), content_type="application/json"
        )
        result = await client.extend_user(user["uuid"], 10)
        assert result["package_days"] == 40

    async def test_future_start_date_counts_as_zero_elapsed(
        self, client: HiddifyClient, panel: FakePanel
    ):
        future = (date.today() + timedelta(days=5)).isoformat()
        user = panel.add_user(package_days=30, start_date=future)
        assert (await client.extend_user(user["uuid"], 10))["package_days"] == 40


class TestSystemEndpoints:
    async def test_server_status(self, client: HiddifyClient):
        data = await client.get_server_status()
        assert data["stats"]["system"]["cpu_percent"] == 12.5

    async def test_update_usage(self, client: HiddifyClient, panel: FakePanel):
        await client.update_usage()
        assert panel.count("GET", "/admin/update_user_usage/") == 1

    async def test_get_logs_uses_form_post(self, client: HiddifyClient):
        assert "line one" in await client.get_logs("panel.log")

    async def test_get_logs_unknown_file(self, client: HiddifyClient):
        with pytest.raises(HiddifyApiError) as exc:
            await client.get_logs("missing.log")
        assert exc.value.status == 404

    async def test_me_and_panel_info(self, client: HiddifyClient):
        assert (await client.get_me())["mode"] == "super_admin"
        assert (await client.get_panel_info())["version"] == "14.0.0b5"


class TestErrors:
    async def test_wrong_api_key_is_403(self, panel: FakePanel):
        bad = HiddifyClient(make_settings(panel.base_url, HIDDIFY_ADMIN_UUID="nope"))
        try:
            with pytest.raises(HiddifyApiError) as exc:
                await bad.get_me()
            assert exc.value.status == 403
            assert "HIDDIFY_ADMIN_UUID" in describe_api_error(exc.value)
        finally:
            await bad.close()

    async def test_wrong_proxy_path_is_a_hinted_bad_request(self, panel: FakePanel):
        bad = HiddifyClient(make_settings(panel.base_url, HIDDIFY_PROXY_PATH="other"))
        try:
            with pytest.raises(HiddifyApiError) as exc:
                await bad.get_me()
            assert exc.value.status == 400
            assert "HIDDIFY_PROXY_PATH" in describe_api_error(exc.value)
        finally:
            await bad.close()

    def test_other_bad_requests_keep_the_panel_message(self):
        assert (
            describe_api_error(HiddifyApiError(400, "User limit reached")) == "User limit reached"
        )

    async def test_server_error_message_comes_from_json(
        self, client: HiddifyClient, panel: FakePanel
    ):
        panel.fail_next(500, "database is locked")
        with pytest.raises(HiddifyApiError) as exc:
            await client.get_me()
        assert exc.value.status == 500
        assert exc.value.message == "database is locked"

    async def test_non_json_error_body_falls_back_to_reason(
        self, client: HiddifyClient, panel: FakePanel
    ):
        panel.respond_next("<html>boom</html>", status=502)
        with pytest.raises(HiddifyApiError) as exc:
            await client.get_me()
        assert exc.value.status == 502
        assert "boom" not in exc.value.message

    async def test_json_array_error_body_falls_back(self, client: HiddifyClient, panel: FakePanel):
        panel.respond_next("[1, 2]", status=500, content_type="application/json")
        with pytest.raises(HiddifyApiError):
            await client.get_me()

    async def test_html_success_page_is_flagged(self, client: HiddifyClient, panel: FakePanel):
        panel.respond_next("<html>login</html>")
        with pytest.raises(HiddifyApiError, match="не JSON"):
            await client.get_me()

    async def test_redirect_is_flagged(self, client: HiddifyClient, panel: FakePanel):
        panel.respond_next("", status=302)
        with pytest.raises(HiddifyApiError, match="HIDDIFY_PROXY_PATH"):
            await client.get_me()

    async def test_unexpected_object_shape(self, client: HiddifyClient, panel: FakePanel):
        panel.respond_next("[1]", content_type="application/json")
        with pytest.raises(HiddifyApiError, match="формат"):
            await client.get_me()

    async def test_connection_refused_is_a_client_error(self):
        dead = HiddifyClient(make_settings("http://127.0.0.1:9"))
        try:
            with pytest.raises(aiohttp.ClientConnectorError) as exc:
                await dead.get_me()
            assert "подключиться" in describe_api_error(exc.value)
        finally:
            await dead.close()

    def test_describe_other_errors(self):
        assert "таймаут" in describe_api_error(TimeoutError())
        assert describe_api_error(ValueError("odd")) == "odd"
        assert describe_api_error(ValueError()) == "ValueError"
        assert HiddifyApiError in API_ERRORS


class TestSession:
    async def test_session_is_reused_and_closed(self, client: HiddifyClient):
        first = await client._get_session()
        assert await client._get_session() is first
        await client.close()
        assert first.closed
        await client.close()
        assert await client._get_session() is not first

    async def test_default_client_lifecycle(self, panel: FakePanel):
        set_client(None)
        default = get_client()
        assert get_client() is default
        await close_client()
        set_client(None)
        await close_client()


def test_admin_uuid_constant_matches_fixture():
    assert make_settings("http://x").admin_uuid == ADMIN_UUID


class TestUserScopeAndPanelExtras:
    async def test_profile_uses_the_client_path_without_the_admin_key(
        self, client: HiddifyClient, panel: FakePanel
    ):
        user = panel.add_user(mode="monthly", package_days=30, start_date=started_ago(10))
        profile = await client.get_user_profile(user["uuid"])
        assert profile["profile_reset_days"] == 20
        assert panel.user_scope_keys == [None]

    async def test_profile_reports_the_no_reset_sentinel(
        self, client: HiddifyClient, panel: FakePanel
    ):
        user = panel.add_user(mode="no_reset")
        assert (await client.get_user_profile(user["uuid"]))["profile_reset_days"] == 10_000

    async def test_profile_for_an_unknown_user_is_an_error(self, client: HiddifyClient):
        with pytest.raises(HiddifyApiError) as exc:
            await client.get_user_profile("00000000-0000-0000-0000-000000000000")
        assert exc.value.status == 302

    async def test_telegram_proxies_when_enabled(self, client: HiddifyClient, panel: FakePanel):
        panel.telegram_proxy = True
        user = panel.add_user()
        proxies = await client.get_telegram_proxies(user["uuid"])
        assert [p["title"] for p in proxies] == ["vpn.example.com", "vpn2.example.com"]
        assert proxies[0]["link"].startswith("tg://proxy?server=vpn.example.com&port=443&secret=ee")

    async def test_telegram_proxies_disabled_is_a_404(
        self, client: HiddifyClient, panel: FakePanel
    ):
        user = panel.add_user()
        with pytest.raises(HiddifyApiError) as exc:
            await client.get_telegram_proxies(user["uuid"])
        assert exc.value.status == 404

    async def test_telegram_proxies_must_be_a_list(self, client: HiddifyClient, panel: FakePanel):
        user = panel.add_user()
        panel.respond_next('{"not": "a list"}', content_type="application/json")
        with pytest.raises(HiddifyApiError, match="формат"):
            await client.get_telegram_proxies(user["uuid"])

    async def test_dashboard(self, client: HiddifyClient):
        data = await client.get_dashboard()
        assert data["users"]["online"]["m5"] == 2
        assert len(data["series"]) == 30

    async def test_nodes_list_ping_and_sync(self, client: HiddifyClient, panel: FakePanel):
        panel.nodes = [node_row(1), node_row(2, status="offline")]
        assert [n["id"] for n in await client.list_nodes()] == [1, 2]
        assert (await client.ping_node(1))["online"] is True
        await client.sync_node(1)
        assert panel.count("POST", "/admin/nodes/1/sync/") == 1

    async def test_failed_sync_is_an_error(self, client: HiddifyClient, panel: FakePanel):
        panel.node_sync_ok = False
        with pytest.raises(HiddifyApiError) as exc:
            await client.sync_node(1)
        assert exc.value.status == 502

    async def test_nodes_payload_must_contain_a_list(self, client: HiddifyClient, panel: FakePanel):
        panel.respond_next('{"nodes": "oops"}', content_type="application/json")
        with pytest.raises(HiddifyApiError, match="формат"):
            await client.list_nodes()

    async def test_user_note_can_be_set_but_not_cleared(
        self, client: HiddifyClient, panel: FakePanel
    ):
        user = panel.add_user()
        assert (await client.update_user(user["uuid"], comment="hello"))["comment"] == "hello"
        assert (await client.update_user(user["uuid"], comment=""))["comment"] == "hello"
