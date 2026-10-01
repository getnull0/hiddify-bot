"""Tests for keyboards.inline keyboard builders."""

from keyboards.inline import (
    admin_main_kb,
    photo_close_kb,
    photo_nav_kb,
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
        assert "my_account" in callbacks
        assert "close" in callbacks


class TestUserActionsKb:
    def test_blocked_user_shows_unblock(self):
        kb = user_actions_kb("uuid-123", limit_gb=0)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "user_unblock:uuid-123" in callbacks
        assert "user_block:uuid-123" not in callbacks

    def test_active_user_shows_block(self):
        kb = user_actions_kb("uuid-123", limit_gb=50)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "user_block:uuid-123" in callbacks
        assert "user_unblock:uuid-123" not in callbacks

    def test_has_extend_buttons(self):
        kb = user_actions_kb("uuid-123", limit_gb=50)
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "user_extend:uuid-123:30" in callbacks
        assert "user_extend:uuid-123:90" in callbacks

    def test_back_button_page_preserved(self):
        kb = user_actions_kb("uuid-123", limit_gb=50, list_page=3)
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
    def test_photo_close(self):
        kb = photo_close_kb()
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert callbacks == ["close"]

    def test_photo_nav_has_back_home_close(self):
        kb = photo_nav_kb(back_cb="my_link", home_cb="user_menu")
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "my_link" in callbacks
        assert "user_menu" in callbacks
        assert "close" in callbacks
