"""Server status, logs and panel info screens."""

from tests.conftest import ADMIN_ID, MEMBER_ID
from tests.fakes.panel import FakePanel
from tests.fakes.telegram import Harness

TELEGRAM_LIMIT = 4096


async def test_server_status(bot: Harness, panel: FakePanel):
    panel.add_user()
    await bot.press("server_status", ADMIN_ID)
    assert "Статус сервера" in bot.last_text
    assert "12.5%" in bot.last_text
    assert "Hiddify: 3.0%" in bot.last_text
    assert "Пользователей: <b>1</b>" in bot.last_text


async def test_update_usage_refreshes_and_reports(bot: Harness, panel: FakePanel):
    await bot.press("update_usage", ADMIN_ID)
    assert panel.count("GET", "/admin/update_user_usage/") == 1
    assert "Трафик обновлён" in bot.last_text
    assert "users_list:0" in bot.last_buttons


async def test_logs_menu_lists_files(bot: Harness):
    await bot.press("logs_menu", ADMIN_ID)
    assert "Выбери лог-файл" in bot.last_text
    assert "logs:panel.log" in bot.last_buttons


async def test_log_view_escapes_content(bot: Harness):
    await bot.press("logs:panel.log", ADMIN_ID)
    assert "line one" in bot.last_text
    assert "line &lt;two&gt; &amp; three" in bot.last_text
    assert "logs_menu" in bot.last_buttons


async def test_missing_log_file_is_explained(bot: Harness):
    await bot.press("logs:backup.log", ADMIN_ID)
    assert "файл не найден" in bot.last_text
    assert bot.alerts == []


async def test_huge_log_fits_into_one_telegram_message(bot: Harness, panel: FakePanel):
    panel.logs["panel.log"] = "<tag> & " * 5000
    await bot.press("logs:panel.log", ADMIN_ID)
    assert len(bot.last_text) <= TELEGRAM_LIMIT
    assert "…" in bot.last_text


async def test_other_log_errors_are_reported(bot: Harness, panel: FakePanel):
    panel.fail_next(500, "disk on fire")
    await bot.press("logs:panel.log", ADMIN_ID)
    assert bot.alerts == ["❌ Ошибка панели: disk on fire"]


async def test_panel_info(bot: Harness):
    await bot.press("panel_info", ADMIN_ID)
    assert "14.0.0b5" in bot.last_text
    assert "Owner (super_admin)" in bot.last_text


async def test_members_cannot_see_server_screens(bot: Harness, panel: FakePanel):
    panel.add_user(telegram_id=MEMBER_ID)
    for data in ("server_status", "logs_menu", "logs:panel.log", "panel_info", "update_usage"):
        await bot.press(data, MEMBER_ID)
    assert bot.edits == []
    assert panel.requests == []
