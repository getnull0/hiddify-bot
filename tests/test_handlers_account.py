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
