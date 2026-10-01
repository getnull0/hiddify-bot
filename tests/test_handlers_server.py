"""Server status, logs and panel info screens."""

from tests.conftest import ADMIN_ID, MEMBER_ID
from tests.fakes.panel import ADMIN_UUID, FakePanel, node_row
from tests.fakes.telegram import Harness

TELEGRAM_LIMIT = 4096


async def test_server_status(bot: Harness, panel: FakePanel):
    panel.add_user()
    await bot.press("server_status", ADMIN_ID)
    assert "Статус сервера" in bot.last_text
    assert "12.5%" in bot.last_text
    assert "Hiddify: 3.0%" in bot.last_text
    assert "Сегодня: <b>2.00 GB</b>" in bot.last_text
    assert "Пользователей" not in bot.last_text


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


async def test_statistics_screen(bot: Harness):
    await bot.press("stats", ADMIN_ID)
    assert "Статистика" in bot.last_text
    assert "Сегодня: <b>2.00 GB</b>" in bot.last_text
    assert "menu" in bot.last_buttons


async def test_statistics_failure_is_reported(bot: Harness, panel: FakePanel):
    panel.fail_next(500, "dashboard broke")
    await bot.press("stats", ADMIN_ID)
    assert bot.alerts == ["❌ Ошибка панели: dashboard broke"]


async def test_status_has_no_servers_button_without_nodes(bot: Harness):
    await bot.press("server_status", ADMIN_ID)
    assert "nodes" not in bot.last_buttons


async def test_status_offers_the_servers_screen_when_nodes_exist(bot: Harness, panel: FakePanel):
    panel.nodes = [node_row(1), node_row(2, status="offline")]
    await bot.press("server_status", ADMIN_ID)
    assert "nodes" in bot.last_buttons
    await bot.press("nodes", ADMIN_ID)
    assert "Серверы (узлы)</b>: 2" in bot.last_text
    assert "🔴 <b>node-2</b>" in bot.last_text
    assert {"node_ping:1", "node_sync:2", "server_status"} <= set(bot.last_buttons)


async def test_nodes_screen_never_shows_the_admin_link(bot: Harness, panel: FakePanel):
    panel.nodes = [node_row(1)]
    await bot.press("nodes", ADMIN_ID)
    assert ADMIN_UUID not in bot.last_text
    assert ADMIN_UUID not in str(bot.last.reply_markup)


async def test_nodes_screen_without_nodes(bot: Harness):
    await bot.press("nodes", ADMIN_ID)
    assert "нет" in bot.last_text
    assert "server_status" in bot.last_buttons


async def test_ping_reports_online_and_offline(bot: Harness, panel: FakePanel):
    panel.nodes = [node_row(1)]
    await bot.press("node_ping:1", ADMIN_ID)
    assert bot.alerts[-1] == "🟢 Отвечает, версия 14.0.0b5"
    panel.node_ping = {"online": False, "version": "", "error": "timeout"}
    await bot.press("node_ping:1", ADMIN_ID)
    assert bot.alerts[-1] == "🔴 Не отвечает: timeout"
    panel.node_ping = {"online": False, "version": "", "error": ""}
    await bot.press("node_ping:1", ADMIN_ID)
    assert bot.alerts[-1] == "🔴 Не отвечает: нет связи"


async def test_online_ping_without_a_version(bot: Harness, panel: FakePanel):
    panel.node_ping = {"online": True, "version": "", "error": ""}
    await bot.press("node_ping:1", ADMIN_ID)
    assert bot.alerts[-1] == "🟢 Отвечает, версия —"


async def test_sync_starts_and_failures_are_reported(bot: Harness, panel: FakePanel):
    await bot.press("node_sync:1", ADMIN_ID)
    assert bot.alerts == ["🔄 Синхронизация запущена"]
    panel.node_sync_ok = False
    await bot.press("node_sync:1", ADMIN_ID)
    assert "не ответил" in bot.alerts[-1] or "did not answer" in bot.alerts[-1]


async def test_members_cannot_use_stats_or_nodes(bot: Harness, panel: FakePanel):
    panel.add_user(telegram_id=MEMBER_ID)
    for data in ("stats", "nodes", "node_ping:1", "node_sync:1"):
        await bot.press(data, MEMBER_ID)
    assert bot.edits == []
    assert bot.alerts == []
