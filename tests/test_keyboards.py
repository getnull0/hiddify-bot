"""Tests for keyboards.nav — pure functions, no external deps."""

from hiddify_bot.keyboards.nav import nav_row, pagination_row


class TestNavRow:
    def test_default(self):
        row = nav_row()
        assert len(row) == 2  # home + close, no back
        assert row[0].callback_data == "menu"
        assert row[1].callback_data == "close"

    def test_with_back(self):
        row = nav_row(back_cb="users_list:2", home_cb="menu")
        assert len(row) == 3
        assert row[0].callback_data == "users_list:2"
        assert row[1].callback_data == "menu"
        assert row[2].callback_data == "close"

    def test_custom_home(self):
        row = nav_row(home_cb="user_menu")
        assert row[0].callback_data == "user_menu"


class TestPaginationRow:
    def test_single_page(self):
        result = pagination_row(0, 1, "users_list")
        assert result is None

    def test_first_page_of_many(self):
        result = pagination_row(0, 3, "users_list")
        assert result is not None
        assert len(result) == 2  # page counter + next
        assert result[0].callback_data == "noop"
        assert result[1].callback_data == "users_list:1"

    def test_middle_page(self):
        result = pagination_row(1, 3, "users_list")
        assert result is not None
        assert len(result) == 3  # prev + counter + next
        assert result[0].callback_data == "users_list:0"
        assert result[1].callback_data == "noop"
        assert result[2].callback_data == "users_list:2"

    def test_last_page(self):
        result = pagination_row(2, 3, "users_list")
        assert result is not None
        assert len(result) == 2  # prev + counter
        assert result[0].callback_data == "users_list:1"
        assert result[1].callback_data == "noop"
