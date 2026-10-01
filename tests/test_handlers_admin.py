"""Admin button flows, driven through the real dispatcher against the fake panel."""

from urllib.parse import quote

import pytest

from tests.conftest import ADMIN_ID, MEMBER_ID, STRANGER_ID
from tests.fakes.panel import FakePanel
from tests.fakes.telegram import Harness


def uuid_of(user: dict) -> str:
    return user["uuid"]


class TestStartAndMenus:
    async def test_admin_start_opens_the_user_menu_with_a_panel_button(self, bot: Harness):
        await bot.text("/start", ADMIN_ID)
        assert bot.last_buttons == ["my_account", "menu", "close"]

    async def test_panel_button_opens_the_admin_menu(self, bot: Harness):
        await bot.text("/start", ADMIN_ID)
        await bot.press("menu", ADMIN_ID)
        assert {"users_list:0", "user_create"} <= set(bot.last_buttons)

    async def test_admin_command_shows_the_full_admin_menu(self, bot: Harness):
        await bot.text("/admin", ADMIN_ID)
        assert {"users_list:0", "user_create", "user_search", "server_status"} <= set(
            bot.last_buttons
        )

    async def test_admin_command_opens_menu_and_clears_state(self, bot: Harness):
        await bot.press("user_create", ADMIN_ID)
        await bot.text("/admin", ADMIN_ID)
        assert "Hiddify Admin" in bot.last_text
        await bot.text("not a name", ADMIN_ID)
        assert "Hiddify Admin" in bot.last_text  # no wizard is active any more

    async def test_unknown_member_is_told_to_contact_admin(self, bot: Harness):
        await bot.text("/start", STRANGER_ID)
        assert "не найден" in bot.last_text
        assert "@support_admin" in bot.last_text
        assert bot.last_buttons == []

    async def test_member_start_opens_user_menu(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.text("/start", MEMBER_ID)
        assert bot.last_buttons == ["my_account", "close"]

    @pytest.mark.parametrize("fields", [{"enable": False}, {"usage_limit_GB": 0.0}])
    async def test_blocked_member_is_turned_away(self, bot: Harness, panel: FakePanel, fields):
        panel.add_user(telegram_id=MEMBER_ID, **fields)
        await bot.text("/start", MEMBER_ID)
        assert "заблокирован" in bot.last_text
        assert "@support_admin" in bot.last_text

    async def test_member_cannot_use_admin_command(self, bot: Harness):
        await bot.text("/admin", STRANGER_ID)
        assert bot.session.calls == []

    async def test_member_cannot_press_admin_buttons(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID)
        for data in ("users_list:0", "user_create", "server_status", "menu"):
            await bot.press(data, MEMBER_ID)
        assert bot.edits == []

    async def test_menu_button_clears_wizard(self, bot: Harness):
        await bot.press("user_create", ADMIN_ID)
        await bot.press("menu", ADMIN_ID)
        assert "Hiddify Admin" in bot.last_text

    async def test_close_deletes_message(self, bot: Harness):
        await bot.press("close", ADMIN_ID)
        assert [type(c).__name__ for c in bot.session.calls] == [
            "AnswerCallbackQuery",
            "DeleteMessage",
        ]

    async def test_noop_only_answers(self, bot: Harness):
        await bot.press("noop", ADMIN_ID)
        assert [type(c).__name__ for c in bot.session.calls] == ["AnswerCallbackQuery"]

    async def test_user_menu_button(self, bot: Harness):
        await bot.press("user_menu", ADMIN_ID)
        assert bot.last_buttons == ["my_account", "menu", "close"]

    async def test_regular_members_never_see_the_panel_button(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.text("/start", MEMBER_ID)
        assert "menu" not in bot.last_buttons
        await bot.press("user_menu", MEMBER_ID)
        assert "menu" not in bot.last_buttons


class TestListAndCard:
    async def test_empty_panel_is_handled(self, bot: Harness):
        await bot.press("users_list:0", ADMIN_ID)
        assert bot.last_text == "Нет пользователей."

    async def test_list_shows_users_with_status_icons(self, bot: Harness, panel: FakePanel):
        panel.add_user(name="Fine")
        panel.add_user(name="Off", enable=False)
        panel.add_user(name="Over", current_usage_GB=99.0)
        await bot.press("users_list:0", ADMIN_ID)
        assert "(3)" in bot.last_text
        labels = [b.text for row in bot.last.reply_markup.inline_keyboard for b in row]
        assert any(t.startswith("✅ Fine") for t in labels)
        assert any(t.startswith("⛔ Off") for t in labels)
        assert any(t.startswith("🟡 Over") for t in labels)

    async def test_pagination_and_back_to_the_same_page(self, bot: Harness, panel: FakePanel):
        users = [panel.add_user(name=f"U{i:02d}") for i in range(10)]
        await bot.press("users_list:1", ADMIN_ID)
        assert len([b for b in bot.last_buttons if b.startswith("user:")]) == 2
        await bot.press(f"user:{uuid_of(users[9])}", ADMIN_ID)
        assert "users_list:1" in bot.last_buttons

    async def test_page_beyond_the_end_is_clamped(self, bot: Harness, panel: FakePanel):
        panel.add_user()
        await bot.press("users_list:5", ADMIN_ID)
        assert len([b for b in bot.last_buttons if b.startswith("user:")]) == 1

    async def test_card_shows_details(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(name="<Mallory>", current_usage_GB=12.5, telegram_id=77)
        await bot.press(f"user:{uuid_of(user)}", ADMIN_ID)
        assert "&lt;Mallory&gt;" in bot.last_text
        assert "12.50 / 50.0 GB" in bot.last_text
        assert "Telegram: 77" in bot.last_text
        assert f"user_block:{uuid_of(user)}" in bot.last_buttons

    async def test_unknown_user_shows_panel_error(self, bot: Harness):
        await bot.press("user:00000000-0000-0000-0000-000000000000", ADMIN_ID)
        assert bot.alerts == ["❌ Ошибка панели: User not found"]
        assert bot.edits == []


class TestBlockAndUnblock:
    async def test_block_disables_user_in_panel(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_block:{uuid_of(user)}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["enable"] is False
        assert "Заблокирован" in bot.last_text
        assert f"user_unblock:{uuid_of(user)}" in bot.last_buttons

    async def test_blocking_a_fresh_zero_usage_user_really_blocks(
        self, bot: Harness, panel: FakePanel
    ):
        user = panel.add_user(current_usage_GB=0.0)
        await bot.press(f"user_block:{uuid_of(user)}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["is_active"] is False

    async def test_unblock_is_one_tap_when_limit_is_kept(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(enable=False)
        await bot.press(f"user_unblock:{uuid_of(user)}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["enable"] is True
        assert "Активен" in bot.last_text
        assert f"user_block:{uuid_of(user)}" in bot.last_buttons

    async def test_legacy_zero_limit_asks_for_a_new_limit(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(usage_limit_GB=0.0)
        await bot.press(f"user:{uuid_of(user)}", ADMIN_ID)
        assert "Заблокирован" in bot.last_text
        await bot.press(f"user_unblock:{uuid_of(user)}", ADMIN_ID)
        assert "новый лимит" in bot.last_text
        for bad in ("abc", "nan", "0", "-5", "1e999"):
            await bot.text(bad, ADMIN_ID)
            assert "положительное число" in bot.last_text
        await bot.text("75", ADMIN_ID)
        assert panel.users[uuid_of(user)]["usage_limit_GB"] == 75.0
        assert "✅ Разблокирован" in bot.last_text
        assert f"user_block:{uuid_of(user)}" in bot.last_buttons


class TestOneTapActions:
    async def test_reset_traffic(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(current_usage_GB=33.0)
        await bot.press(f"user_reset:{uuid_of(user)}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["current_usage_GB"] == 0
        assert "0.00 / 50.0 GB" in bot.last_text

    @pytest.mark.parametrize("days", [30, 90])
    async def test_extend(self, bot: Harness, panel: FakePanel, days):
        user = panel.add_user(package_days=30)
        await bot.press(f"user_extend:{uuid_of(user)}:{days}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["package_days"] == 30 + days
        assert bot.alerts == [f"⏱ +{days} дней"]

    async def test_mode_menu_and_change(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_set_mode:{uuid_of(user)}", ADMIN_ID)
        assert f"user_mode:{uuid_of(user)}:monthly" in bot.last_buttons
        await bot.press(f"user_mode:{uuid_of(user)}:monthly", ADMIN_ID)
        assert panel.users[uuid_of(user)]["mode"] == "monthly"
        assert bot.alerts[-1] == "✅ ежемесячно"
        assert "ежемесячно" in bot.last_text

    async def test_unknown_mode_is_rejected(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_mode:{uuid_of(user)}:bogus", ADMIN_ID)
        assert bot.alerts == ["❌ Неизвестный режим"]
        assert panel.users[uuid_of(user)]["mode"] == "no_reset"

    async def test_delete_with_confirmation_returns_to_the_list_page(
        self, bot: Harness, panel: FakePanel
    ):
        user = panel.add_user()
        await bot.press("users_list:0", ADMIN_ID)
        await bot.press(f"user_delete_confirm:{uuid_of(user)}", ADMIN_ID)
        assert "необратимо" in bot.last_text
        assert f"user_delete:{uuid_of(user)}" in bot.last_buttons
        await bot.press(f"user_delete:{uuid_of(user)}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["deleted"] is True
        assert "удалён" in bot.last_text
        assert "users_list:0" in bot.last_buttons

    async def test_cancelling_delete_returns_to_the_card(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_delete_confirm:{uuid_of(user)}", ADMIN_ID)
        await bot.press(f"user:{uuid_of(user)}", ADMIN_ID)
        assert user["name"] in bot.last_text
        assert panel.users[uuid_of(user)]["deleted"] is False


class TestEditWizards:
    async def test_set_limit(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_set_limit:{uuid_of(user)}", ADMIN_ID)
        assert "лимит трафика" in bot.last_text
        for bad in ("abc", "0", "-1", "nan", "2000000"):
            await bot.text(bad, ADMIN_ID)
            assert "положительное число" in bot.last_text
        await bot.non_text(ADMIN_ID)
        assert "положительное число" in bot.last_text
        await bot.text("12.5", ADMIN_ID)
        assert panel.users[uuid_of(user)]["usage_limit_GB"] == 12.5
        assert "12.5 GB" in bot.last_text

    async def test_set_days(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_set_days:{uuid_of(user)}", ADMIN_ID)
        for bad in ("x", "0", "-3", "1.5", "99999999"):
            await bot.text(bad, ADMIN_ID)
            assert "число дней" in bot.last_text
        await bot.text("45", ADMIN_ID)
        assert panel.users[uuid_of(user)]["package_days"] == 45

    async def test_set_telegram_id(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_set_tgid:{uuid_of(user)}", ADMIN_ID)
        for bad in ("abc", "0", "-5"):
            await bot.text(bad, ADMIN_ID)
            assert "Telegram ID" in bot.last_text
            assert bot.last_text.startswith("❌")
        await bot.text("555", ADMIN_ID)
        assert panel.users[uuid_of(user)]["telegram_id"] == 555
        assert "✅ Telegram ID 555 привязан." in bot.last_text

    async def test_cancel_returns_to_the_card(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(name="Cancelled")
        await bot.press(f"user_set_limit:{uuid_of(user)}", ADMIN_ID)
        await bot.press(f"fsm_cancel:user:{uuid_of(user)}", ADMIN_ID)
        assert "Cancelled" in bot.last_text
        assert bot.alerts[-1] == "Отменено"
        await bot.text("99", ADMIN_ID)  # wizard is over, so this must not change anything
        assert panel.users[uuid_of(user)]["usage_limit_GB"] == 50.0

    async def test_panel_error_keeps_the_wizard_alive(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_set_limit:{uuid_of(user)}", ADMIN_ID)
        panel.fail_next(500, "database <locked>")
        await bot.text("10", ADMIN_ID)
        assert bot.last_text == "❌ Ошибка панели: database &lt;locked&gt;"
        await bot.text("10", ADMIN_ID)
        assert panel.users[uuid_of(user)]["usage_limit_GB"] == 10.0


class TestCreateWizard:
    async def test_defaults_everywhere(self, bot: Harness, panel: FakePanel):
        await bot.press("user_create", ADMIN_ID)
        assert "имя" in bot.last_text
        for answer in ("Newbie", ".", ".", "."):
            await bot.text(answer, ADMIN_ID)
        (created,) = panel.users.values()
        assert (created["name"], created["package_days"], created["usage_limit_GB"]) == (
            "Newbie",
            30,
            50.0,
        )
        assert created["telegram_id"] is None
        assert "✅ Создан!" in bot.last_text
        assert f"user_block:{created['uuid']}" in bot.last_buttons

    async def test_custom_values(self, bot: Harness, panel: FakePanel):
        await bot.press("user_create", ADMIN_ID)
        for answer in ("Zed", "7", "1.5", "999"):
            await bot.text(answer, ADMIN_ID)
        (created,) = panel.users.values()
        assert (created["package_days"], created["usage_limit_GB"], created["telegram_id"]) == (
            7,
            1.5,
            999,
        )

    async def test_each_step_validates_its_input(self, bot: Harness, panel: FakePanel):
        await bot.press("user_create", ADMIN_ID)
        for bad in ("", "x" * 65):
            await bot.text(bad, ADMIN_ID) if bad else await bot.non_text(ADMIN_ID)
            assert "от 1 до 64" in bot.last_text
        await bot.text("Valid", ADMIN_ID)
        for bad in ("x", "0", "-1"):
            await bot.text(bad, ADMIN_ID)
            assert "или . для пропуска" in bot.last_text
        await bot.text("10", ADMIN_ID)
        for bad in ("x", "-1", "inf"):
            await bot.text(bad, ADMIN_ID)
            assert "или . для пропуска" in bot.last_text
        await bot.text("5", ADMIN_ID)
        for bad in ("x", "-1", "0"):
            await bot.text(bad, ADMIN_ID)
            assert "или . для пропуска" in bot.last_text
        assert panel.users == {}

    async def test_back_button_walks_through_the_steps(self, bot: Harness):
        await bot.press("user_create", ADMIN_ID)
        await bot.text("Name", ADMIN_ID)
        await bot.text("5", ADMIN_ID)
        await bot.text("5", ADMIN_ID)
        assert "Telegram ID" in bot.last_text
        await bot.press("fsm_back", ADMIN_ID)
        assert "Лимит трафика" in bot.last_text
        await bot.press("fsm_back", ADMIN_ID)
        assert "Количество дней" in bot.last_text
        await bot.press("fsm_back", ADMIN_ID)
        assert "имя" in bot.last_text
        assert "fsm_back" not in bot.last_buttons

    async def test_back_without_a_wizard_does_nothing(self, bot: Harness):
        await bot.press("fsm_back", ADMIN_ID)
        assert bot.edits == []

    async def test_panel_refusal_keeps_the_last_step(self, bot: Harness, panel: FakePanel):
        panel.max_users = 0
        await bot.press("user_create", ADMIN_ID)
        for answer in ("Capped", ".", ".", "."):
            await bot.text(answer, ADMIN_ID)
        assert "User limit reached" in bot.last_text
        panel.max_users = None
        await bot.text(".", ADMIN_ID)
        assert len(panel.users) == 1

    async def test_cancel_goes_back_to_the_menu(self, bot: Harness):
        await bot.press("user_create", ADMIN_ID)
        await bot.press("fsm_cancel:menu", ADMIN_ID)
        assert "Hiddify Admin" in bot.last_text


class TestSearch:
    async def test_single_match_opens_the_card(self, bot: Harness, panel: FakePanel):
        panel.add_user(name="Anna")
        panel.add_user(name="Bob")
        await bot.press("user_search", ADMIN_ID)
        await bot.text("anna", ADMIN_ID)
        assert "Anna" in bot.last_text
        assert any(b.startswith("user_block:") for b in bot.last_buttons)

    async def test_many_matches_show_a_list(self, bot: Harness, panel: FakePanel):
        panel.add_user(name="Anna")
        panel.add_user(name="Hanna")
        await bot.press("user_search", ADMIN_ID)
        await bot.text("ann", ADMIN_ID)
        assert "найдено: 2" in bot.last_text
        assert len([b for b in bot.last_buttons if b.startswith("user:")]) == 2

    async def test_no_match(self, bot: Harness, panel: FakePanel):
        panel.add_user(name="Anna")
        await bot.press("user_search", ADMIN_ID)
        await bot.text("<zzz>", ADMIN_ID)
        assert "ничего не найдено" in bot.last_text
        assert "&lt;zzz&gt;" in bot.last_text

    async def test_non_text_input_is_re_prompted(self, bot: Harness):
        await bot.press("user_search", ADMIN_ID)
        await bot.non_text(ADMIN_ID)
        assert "текстом" in bot.last_text
        await bot.press("fsm_cancel:menu", ADMIN_ID)
        assert "Hiddify Admin" in bot.last_text


class TestLinkQrApps:
    async def test_link_screen(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_link:{uuid_of(user)}", ADMIN_ID)
        assert f"/userpath/{uuid_of(user)}/" in bot.last_text
        assert f"user_qr:{uuid_of(user)}" in bot.last_buttons

    async def test_qr_photo_encodes_the_subscription_url(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_qr:{uuid_of(user)}", ADMIN_ID)
        (photo,) = bot.photos
        sub_url = f"http://panel.test/userpath/{uuid_of(user)}/"
        assert quote(sub_url, safe="") in photo.photo.url
        assert photo.photo.url.startswith("https://api.qrserver.com/")
        assert sub_url.split("//")[1] in bot.last_text
        assert f"user_link:{uuid_of(user)}" in bot.last_buttons

    async def test_apps_screen_has_download_links(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        await bot.press(f"user_apps:{uuid_of(user)}", ADMIN_ID)
        assert "Приложения" in bot.last_text
        assert any(b.startswith("https://") for b in bot.last_buttons)
        assert f"user:{uuid_of(user)}" in bot.last_buttons


class TestPanelFailures:
    async def test_list_failure_is_reported_not_crashed(self, bot: Harness, panel: FakePanel):
        panel.add_user()
        panel.fail_next(502, "bad gateway")
        await bot.press("users_list:0", ADMIN_ID)
        assert bot.alerts == ["❌ Ошибка панели: bad gateway"]

    async def test_forbidden_gives_a_configuration_hint(self, bot: Harness, panel: FakePanel):
        panel.add_user()
        panel.fail_next(403, "Unathorized")
        await bot.press("users_list:0", ADMIN_ID)
        assert "HIDDIFY_ADMIN_UUID" in bot.alerts[0]

    async def test_block_failure_changes_nothing(self, bot: Harness, panel: FakePanel):
        user = panel.add_user()
        panel.fail_next(500, "nope")
        await bot.press(f"user_block:{uuid_of(user)}", ADMIN_ID)
        assert panel.users[uuid_of(user)]["enable"] is True
        assert bot.edits == []
