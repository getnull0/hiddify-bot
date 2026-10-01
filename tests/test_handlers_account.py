"""The self-service account screens for admins and regular members."""

from tests.conftest import ADMIN_ID, MEMBER_ID, STRANGER_ID
from tests.fakes.panel import FakePanel, started_ago
from tests.fakes.telegram import Harness


class TestMemberAccount:
    async def test_account_card(self, bot: Harness, panel: FakePanel):
        panel.add_user(
            name="Mia",
            telegram_id=MEMBER_ID,
            current_usage_GB=10.0,
            package_days=30,
            start_date=started_ago(5),
            mode="monthly",
        )
        await bot.press("my_account", MEMBER_ID)
        assert "Mia" in bot.last_text
        assert "10.00 / 50.0 GB" in bot.last_text
        assert "25 дн." in bot.last_text
        assert "ежемесячно" in bot.last_text
        assert set(bot.last_buttons) == {"my_link", "my_apps", "user_menu", "close"}

    async def test_expired_account_is_flagged(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID, package_days=5, start_date=started_ago(20))
        await bot.press("my_account", MEMBER_ID)
        assert "истёк" in bot.last_text

    async def test_unknown_member_gets_a_friendly_message(self, bot: Harness):
        await bot.press("my_account", STRANGER_ID)
        assert "Аккаунт не найден" in bot.last_text
        assert bot.last_buttons == ["user_menu", "close"]

    async def test_link_screen(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("my_link", MEMBER_ID)
        assert f"/userpath/{user['uuid']}/" in bot.last_text
        assert "my_qr" in bot.last_buttons
        assert "my_account" in bot.last_buttons

    async def test_link_for_unknown_member(self, bot: Harness):
        await bot.press("my_link", STRANGER_ID)
        assert "Аккаунт не найден" in bot.last_text

    async def test_qr_photo(self, bot: Harness, panel: FakePanel):
        user = panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("my_qr", MEMBER_ID)
        (photo,) = bot.photos
        assert user["uuid"] in photo.photo.url
        assert "Отсканируй QR-код" in bot.last_text
        assert "my_link" in bot.last_buttons
        assert "user_menu" in bot.last_buttons

    async def test_qr_for_unknown_member(self, bot: Harness):
        await bot.press("my_qr", STRANGER_ID)
        assert bot.photos == []
        assert "Аккаунт не найден" in bot.last_text

    async def test_apps_screen(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("my_apps", MEMBER_ID)
        assert "Приложения" in bot.last_text
        assert "my_account" in bot.last_buttons

    async def test_apps_for_unknown_member(self, bot: Harness):
        await bot.press("my_apps", STRANGER_ID)
        assert "Аккаунт не найден" in bot.last_text


class TestAdminOwnAccount:
    async def test_linked_admin_sees_their_account(self, bot: Harness, panel: FakePanel):
        panel.add_user(name="Boss", telegram_id=ADMIN_ID)
        await bot.press("admin_my_account", ADMIN_ID)
        assert "Boss" in bot.last_text
        assert "menu" in bot.last_buttons

    async def test_unlinked_admin_gets_instructions(self, bot: Harness):
        await bot.press("admin_my_account", ADMIN_ID)
        assert "не привязан" in bot.last_text
        assert "menu" in bot.last_buttons

    async def test_admin_navigation_uses_admin_menu(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=ADMIN_ID)
        await bot.press("my_link", ADMIN_ID)
        assert "admin_my_account" in bot.last_buttons
        assert "menu" in bot.last_buttons
        await bot.press("my_apps", ADMIN_ID)
        assert "admin_my_account" in bot.last_buttons
        await bot.press("my_qr", ADMIN_ID)
        assert "menu" in bot.last_buttons

    async def test_member_cannot_open_the_admin_variant(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("admin_my_account", MEMBER_ID)
        assert bot.edits == []


class TestResetDaysAndTelegramProxy:
    async def test_card_shows_days_to_reset(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID, mode="monthly", start_date=started_ago(5))
        await bot.press("my_account", MEMBER_ID)
        assert "ежемесячно, через 25 дн." in bot.last_text

    async def test_no_reset_mode_has_no_countdown(self, bot: Harness, panel: FakePanel):
        panel.add_user(telegram_id=MEMBER_ID, mode="no_reset")
        await bot.press("my_account", MEMBER_ID)
        assert "через" not in bot.last_text

    async def test_proxy_button_is_hidden_when_the_panel_has_no_proxy(
        self, bot: Harness, panel: FakePanel
    ):
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("my_account", MEMBER_ID)
        assert "my_proxy" not in bot.last_buttons

    async def test_proxy_screen_offers_telegram_links(self, bot: Harness, panel: FakePanel):
        panel.telegram_proxy = True
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("my_account", MEMBER_ID)
        assert "my_proxy" in bot.last_buttons
        await bot.press("my_proxy", MEMBER_ID)
        assert "Прокси для Telegram" in bot.last_text
        links = [b for b in bot.last_buttons if b.startswith("tg://proxy?")]
        assert len(links) == 2
        assert "my_account" in bot.last_buttons
        assert "user_menu" in bot.last_buttons

    async def test_proxy_screen_when_it_was_switched_off_meanwhile(
        self, bot: Harness, panel: FakePanel
    ):
        panel.add_user(telegram_id=MEMBER_ID)
        await bot.press("my_proxy", MEMBER_ID)
        assert "не включён" in bot.last_text
        assert bot.alerts == []

    async def test_proxy_for_unknown_member(self, bot: Harness):
        await bot.press("my_proxy", STRANGER_ID)
        assert "Аккаунт не найден" in bot.last_text

    async def test_admin_navigation_uses_the_admin_menu(self, bot: Harness, panel: FakePanel):
        panel.telegram_proxy = True
        panel.add_user(telegram_id=ADMIN_ID)
        await bot.press("my_proxy", ADMIN_ID)
        assert "admin_my_account" in bot.last_buttons
        assert "menu" in bot.last_buttons

    async def test_account_still_works_on_panels_without_the_user_api(
        self, bot: Harness, panel: FakePanel
    ):
        panel.user_api_available = False
        panel.add_user(name="Old", telegram_id=MEMBER_ID, mode="monthly")
        await bot.press("my_account", MEMBER_ID)
        assert "Old" in bot.last_text
        assert "через" not in bot.last_text
        assert "my_proxy" not in bot.last_buttons
