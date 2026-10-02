from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from hiddify_bot.formatters.user import status_icon
from hiddify_bot.keyboards.nav import nav_row, pagination_row
from hiddify_bot.utils.types import JsonDict
from hiddify_bot.utils.user_state import limit_gb

# ── Admin menus ───────────────────────────────────────────────────────────────


def admin_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="users_list:0"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="user_create"),
    )
    kb.row(
        InlineKeyboardButton(text="🔍 Найти", callback_data="user_search"),
        InlineKeyboardButton(text="📊 Сервер", callback_data="server_status"),
    )
    kb.row(
        InlineKeyboardButton(text="📈 Статистика", callback_data="stats"),
    )
    kb.row(
        InlineKeyboardButton(text="📋 Логи", callback_data="logs_menu"),
    )
    kb.row(
        InlineKeyboardButton(text="🔄 Обновить трафик", callback_data="update_usage"),
    )
    kb.row(
        InlineKeyboardButton(text="👤 Мой аккаунт (VPN)", callback_data="admin_my_account"),
    )
    kb.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="close", style="primary"))
    return kb.as_markup()


def users_list_kb(users: list[JsonDict], page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    page = min(max(page, 0), max(0, (len(users) - 1) // page_size))
    start = page * page_size
    chunk = users[start : start + page_size]

    for u in chunk:
        used = u.get("current_usage_GB") or 0.0
        label = f"{status_icon(u)} {u.get('name', '—')} · {used:.1f}/{limit_gb(u):.0f}GB"
        kb.row(InlineKeyboardButton(text=label, callback_data=f"user:{u['uuid']}"))

    total_pages = max(1, (len(users) - 1) // page_size + 1)
    pag = pagination_row(page, total_pages, "users_list")
    if pag:
        kb.row(*pag)

    kb.row(*nav_row(home_cb="menu"))
    return kb.as_markup()


def user_actions_kb(uuid: str, blocked: bool, list_page: int = 0) -> InlineKeyboardMarkup:
    """Action buttons for a user card; the first button toggles block state."""
    kb = InlineKeyboardBuilder()

    if blocked:
        kb.row(
            InlineKeyboardButton(
                text="✅ Разблокировать", callback_data=f"user_unblock:{uuid}", style="success"
            )
        )
    else:
        kb.row(
            InlineKeyboardButton(
                text="🔴 Заблокировать", callback_data=f"user_block:{uuid}", style="danger"
            )
        )

    kb.row(
        InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"user_link:{uuid}"),
        InlineKeyboardButton(text="🔄 Сбросить трафик", callback_data=f"user_reset:{uuid}"),
    )
    kb.row(
        InlineKeyboardButton(text="⏱ +30 дней", callback_data=f"user_extend:{uuid}:30"),
        InlineKeyboardButton(text="⏱ +90 дней", callback_data=f"user_extend:{uuid}:90"),
    )
    kb.row(
        InlineKeyboardButton(text="📦 Лимит GB", callback_data=f"user_set_limit:{uuid}"),
        InlineKeyboardButton(text="📅 Дней", callback_data=f"user_set_days:{uuid}"),
    )
    kb.row(
        InlineKeyboardButton(text="🔁 Режим сброса", callback_data=f"user_set_mode:{uuid}"),
        InlineKeyboardButton(text="🔗 Telegram ID", callback_data=f"user_set_tgid:{uuid}"),
    )
    kb.row(InlineKeyboardButton(text="💬 Заметка", callback_data=f"user_set_comment:{uuid}"))
    kb.row(
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"user_delete_confirm:{uuid}", style="danger"
        )
    )
    kb.row(*nav_row(back_cb=f"users_list:{list_page}", home_cb="menu"))
    return kb.as_markup()


def user_mode_kb(uuid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📅 Ежемесячно", callback_data=f"user_mode:{uuid}:monthly"),
        InlineKeyboardButton(text="📆 Еженедельно", callback_data=f"user_mode:{uuid}:weekly"),
    )
    kb.row(
        InlineKeyboardButton(text="🗓 Ежедневно", callback_data=f"user_mode:{uuid}:daily"),
        InlineKeyboardButton(text="∞ Без сброса", callback_data=f"user_mode:{uuid}:no_reset"),
    )
    kb.row(*nav_row(back_cb=f"user:{uuid}", home_cb="menu"))
    return kb.as_markup()


def confirm_delete_kb(uuid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="◀️ Отмена", callback_data=f"user:{uuid}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"user_delete:{uuid}"),
    )
    return kb.as_markup()


_LOG_FILES = [
    ("hiddify_panel.out.log", "🖥 Панель (вывод)"),
    ("hiddify_panel.err.log", "🔴 Панель (ошибки)"),
    ("hiddify_panel_background_tasks.out.log", "⚙️ Фон (вывод)"),
    ("hiddify_panel_background_tasks.err.log", "🔴 Фон (ошибки)"),
    ("restart.log", "🔄 Перезапуск"),
    ("panel.log", "📋 panel.log"),
    ("backup.log", "💾 Бэкап"),
    ("daily_actions.log", "📅 Ежедневные задачи"),
]


def logs_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for filename, label in _LOG_FILES:
        kb.row(InlineKeyboardButton(text=label, callback_data=f"logs:{filename}"))
    kb.row(*nav_row(home_cb="menu"))
    return kb.as_markup()


def user_link_kb(uuid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📸 QR-код", callback_data=f"user_qr:{uuid}"))
    kb.row(*nav_row(back_cb=f"user:{uuid}", home_cb="menu"))
    return kb.as_markup()


def my_link_kb(back_cb: str = "my_account", home_cb: str = "user_menu") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📸 QR-код", callback_data="my_qr"))
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()


def my_account_kb(home_cb: str = "menu", proxy: bool = False) -> InlineKeyboardMarkup:
    """Buttons under the own-account card; the Telegram proxy one only if the panel offers it."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔑 Ссылка", callback_data="my_link"),
        InlineKeyboardButton(text="📱 Приложения", callback_data="my_apps"),
    )
    if proxy:
        kb.row(InlineKeyboardButton(text="📡 Прокси для Telegram", callback_data="my_proxy"))
    kb.row(*nav_row(home_cb=home_cb))
    return kb.as_markup()


def generic_back_kb(back_cb: str | None = None, home_cb: str = "menu") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()


def fsm_cancel_kb(back_cb: str = "menu") -> InlineKeyboardMarkup:
    """Cancel button only, for single-step wizards."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="❌ Отмена", callback_data=f"fsm_cancel:{back_cb}", style="danger"
        )
    )
    return kb.as_markup()


def fsm_nav_kb(back_cb: str = "menu", has_prev: bool = False) -> InlineKeyboardMarkup:
    """Navigation for multi-step wizards: [Back] + [Cancel]."""
    kb = InlineKeyboardBuilder()
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(text="◀️ Назад", callback_data="fsm_back", style="primary"))
    row.append(
        InlineKeyboardButton(
            text="❌ Отмена", callback_data=f"fsm_cancel:{back_cb}", style="danger"
        )
    )
    kb.row(*row)
    return kb.as_markup()


# ── User menus ────────────────────────────────────────────────────────────────


def user_main_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Мой аккаунт", callback_data="my_account"))
    if is_admin:
        kb.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="menu"))
    kb.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="close", style="primary"))
    return kb.as_markup()


def user_generic_back_kb() -> InlineKeyboardMarkup:
    return generic_back_kb(home_cb="user_menu")


def photo_nav_kb(back_cb: str | None = None, home_cb: str = "menu") -> InlineKeyboardMarkup:
    """Navigation for photo messages: [Back] [Home] [Close]."""
    return generic_back_kb(back_cb=back_cb, home_cb=home_cb)


def apps_kb(back_cb: str = "my_account", home_cb: str = "user_menu") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🤖 Hiddify Android",
            url="https://play.google.com/store/apps/details?id=app.hiddify.com",
        ),
        InlineKeyboardButton(text="🍎 Hiddify iOS", url="https://apps.apple.com/app/id6596777532"),
    )
    kb.row(
        InlineKeyboardButton(
            text="💻 Hiddify Desktop (GitHub)",
            url="https://github.com/hiddify/hiddify-app/releases/latest",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="🤖 v2rayNG", url="https://github.com/2dust/v2rayNG/releases/latest"
        ),
        InlineKeyboardButton(text="🍎 Streisand", url="https://apps.apple.com/app/id6450534064"),
    )
    kb.row(
        InlineKeyboardButton(
            text="🤖 NekoBox",
            url="https://github.com/MatsuriDayo/NekoBoxForAndroid/releases/latest",
        ),
        InlineKeyboardButton(
            text="💻 Nekoray", url="https://github.com/MatsuriDayo/nekoray/releases/latest"
        ),
    )
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()


_MAX_PROXY_BUTTONS = 8
_NAME_MAX = 18


def proxy_kb(proxies: list[JsonDict], back_cb: str, home_cb: str) -> InlineKeyboardMarkup:
    """One URL button per Telegram proxy link; tapping it offers to enable the proxy."""
    kb = InlineKeyboardBuilder()
    for proxy in proxies[:_MAX_PROXY_BUTTONS]:
        title = str(proxy.get("title") or "proxy")[:_NAME_MAX]
        kb.row(InlineKeyboardButton(text=f"📡 {title}", url=str(proxy["link"])))
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()


def server_status_kb(node_count: int = 0) -> InlineKeyboardMarkup:
    """Back/Home row, plus a Servers button when the panel has remote nodes."""
    kb = InlineKeyboardBuilder()
    if node_count:
        kb.row(InlineKeyboardButton(text=f"🌐 Серверы ({node_count})", callback_data="nodes"))
    kb.row(*nav_row(home_cb="menu"))
    return kb.as_markup()


def nodes_kb(nodes: list[JsonDict]) -> InlineKeyboardMarkup:
    """Ping and sync buttons for every node."""
    kb = InlineKeyboardBuilder()
    for node in nodes:
        name = str(node.get("name") or f"node-{node['id']}")[:_NAME_MAX]
        kb.row(
            InlineKeyboardButton(text=f"📶 {name}", callback_data=f"node_ping:{node['id']}"),
            InlineKeyboardButton(text="🔄 Синхр.", callback_data=f"node_sync:{node['id']}"),
        )
    kb.row(*nav_row(back_cb="server_status", home_cb="menu"))
    return kb.as_markup()
