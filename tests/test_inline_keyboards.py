"""Tests for keyboards.inline keyboard builders."""

from keyboards.inline import (
    admin_main_kb,
    my_account_kb,
    nodes_kb,
    photo_nav_kb,
    proxy_kb,
    server_status_kb,
    user_actions_kb,
    user_main_kb,
    users_list_kb,
)


class TestAdminMainKb:
    def test_has_required_buttons(self):
        kb = admin_main_kb()
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "users_list:0" in callbacks
        assert "user_create" in callbacks
        assert "user_search" in callbacks
        assert "server_status" in callbacks
        assert "logs_menu" in callbacks
        assert "update_usage" in callbacks
        assert "admin_my_account" in callbacks
        assert "close" in callbacks


class TestUserMainKb:
    def test_has_account_and_close(self):
        kb = user_main_kb()
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert callbacks == ["my_account", "close"]

    def test_admin_gets_a_panel_button(self):
        kb = user_main_kb(is_admin=True)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert callbacks == ["my_account", "menu", "close"]


class TestUserActionsKb:
    def test_blocked_user_shows_unblock(self):
        kb = user_actions_kb("uuid-123", blocked=True)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "user_unblock:uuid-123" in callbacks
        assert "user_block:uuid-123" not in callbacks

    def test_active_user_shows_block(self):
        kb = user_actions_kb("uuid-123", blocked=False)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "user_block:uuid-123" in callbacks
        assert "user_unblock:uuid-123" not in callbacks

    def test_has_extend_buttons(self):
        kb = user_actions_kb("uuid-123", blocked=False)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "user_extend:uuid-123:30" in callbacks
        assert "user_extend:uuid-123:90" in callbacks

    def test_back_button_page_preserved(self):
        kb = user_actions_kb("uuid-123", blocked=False, list_page=3)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "users_list:3" in callbacks
        assert "users_list:0" not in callbacks


class TestUsersListKb:
    def test_empty_list(self):
        kb = users_list_kb([], page=0)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        # Should still have nav (back/home/close)
        assert "close" in callbacks

    def test_pagination(self):
        users = [
            {
                "uuid": f"u{i}",
                "name": f"User{i}",
                "enable": True,
                "usage_limit_GB": 50,
                "current_usage_GB": 0,
            }
            for i in range(20)
        ]
        kb = users_list_kb(users, page=0)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        # Should have next button
        assert "users_list:1" in callbacks

    def test_page_size(self):
        users = [
            {
                "uuid": f"u{i}",
                "name": f"User{i}",
                "enable": True,
                "usage_limit_GB": 50,
                "current_usage_GB": 0,
            }
            for i in range(20)
        ]
        kb = users_list_kb(users, page=0, page_size=8)
        user_buttons = [
            btn
            for row in kb.inline_keyboard
            for btn in row
            if btn.callback_data.startswith("user:")
        ]
        assert len(user_buttons) == 8


class TestPhotoKeyboards:
    def test_photo_nav_has_back_home_close(self):
        kb = photo_nav_kb(back_cb="my_link", home_cb="user_menu")
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "my_link" in callbacks
        assert "user_menu" in callbacks
        assert "close" in callbacks


class TestV14Keyboards:
    @staticmethod
    def _buttons(kb):
        return [b for row in kb.inline_keyboard for b in row]

    def test_admin_menu_has_statistics(self):
        assert "stats" in [b.callback_data for b in self._buttons(admin_main_kb())]

    def test_user_card_has_a_note_button(self):
        kb = user_actions_kb("u1", blocked=False)
        assert "user_set_comment:u1" in [b.callback_data for b in self._buttons(kb)]

    def test_proxy_button_only_when_offered(self):
        assert "my_proxy" not in [b.callback_data for b in self._buttons(my_account_kb())]
        kb = my_account_kb(proxy=True)
        assert "my_proxy" in [b.callback_data for b in self._buttons(kb)]

    def test_proxy_keyboard_has_url_buttons_and_navigation(self):
        proxies = [{"title": "vpn.example.com", "link": "tg://proxy?server=a&port=443&secret=ee"}]
        buttons = self._buttons(proxy_kb(proxies, "my_account", "user_menu"))
        assert buttons[0].url == "tg://proxy?server=a&port=443&secret=ee"
        assert {"my_account", "user_menu", "close"} <= {b.callback_data for b in buttons[1:]}

    def test_proxy_keyboard_is_capped_and_titles_truncated(self):
        proxies = [{"title": "x" * 60, "link": f"tg://proxy?server={i}"} for i in range(20)]
        buttons = self._buttons(proxy_kb(proxies, "b", "h"))
        assert len([b for b in buttons if b.url]) == 8
        assert len(buttons[0].text) <= 3 + 18

    def test_status_keyboard_shows_servers_only_when_there_are_nodes(self):
        assert "nodes" not in [b.callback_data for b in self._buttons(server_status_kb(0))]
        kb = server_status_kb(2)
        button = next(b for b in self._buttons(kb) if b.callback_data == "nodes")
        assert "(2)" in button.text

    def test_nodes_keyboard_pings_and_syncs_each_node(self):
        kb = nodes_kb([{"id": 7, "name": "edge"}, {"id": 9}])
        callbacks = [b.callback_data for b in self._buttons(kb)]
        assert {"node_ping:7", "node_sync:7", "node_ping:9", "node_sync:9", "server_status"} <= set(
            callbacks
        )
