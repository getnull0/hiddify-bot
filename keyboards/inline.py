from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.nav import nav_row, pagination_row


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


def users_list_kb(users: list[dict], page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * page_size
    chunk = users[start:start + page_size]

    for u in chunk:
        active = u.get("is_active", False)
        enabled = u.get("enable", False)
        limit = u.get("usage_limit_GB") or 0.0
        if limit == 0:
            status = "⛔"
        elif active:
            status = "✅"
        elif enabled:
            status = "🟡"
        else:
            status = "⛔"
        used = u.get("current_usage_GB") or 0.0
        label = f"{status} {u.get('name', '—')} · {used:.1f}/{limit:.0f}GB"
        kb.row(InlineKeyboardButton(text=label, callback_data=f"user:{u['uuid']}"))

    total_pages = max(1, (len(users) - 1) // page_size + 1)
    pag = pagination_row(page, total_pages, "users_list")
    if pag:
        kb.row(*pag)

    kb.row(*nav_row(home_cb="menu"))
    return kb.as_markup()


def user_actions_kb(uuid: str, limit_gb: float, list_page: int = 0) -> InlineKeyboardMarkup:
    """limit_gb == 0 → пользователь заблокирован (нужен визард для разблокировки)."""
    kb = InlineKeyboardBuilder()

    if limit_gb == 0:
        kb.row(InlineKeyboardButton(
            text="✅ Разблокировать", callback_data=f"user_unblock:{uuid}", style="success"
        ))
    else:
        kb.row(InlineKeyboardButton(
            text="🔴 Заблокировать", callback_data=f"user_block:{uuid}", style="danger"
        ))

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
    kb.row(InlineKeyboardButton(
        text="🗑 Удалить", callback_data=f"user_delete_confirm:{uuid}", style="danger"
    ))
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


def my_account_kb(home_cb: str = "menu") -> InlineKeyboardMarkup:
    """Кнопки под карточкой своего аккаунта (и для админа и для юзера)."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔑 Ссылка", callback_data="my_link"),
        InlineKeyboardButton(text="📱 Приложения", callback_data="my_apps"),
    )
    kb.row(*nav_row(home_cb=home_cb))
    return kb.as_markup()


def generic_back_kb(back_cb: str = None, home_cb: str = "menu") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()


def fsm_cancel_kb(back_cb: str = "menu") -> InlineKeyboardMarkup:
    """Только кнопка отмены — для одношаговых визардов."""
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="❌ Отмена", callback_data=f"fsm_cancel:{back_cb}", style="danger"
    ))
    return kb.as_markup()


def fsm_nav_kb(back_cb: str = "menu", has_prev: bool = False) -> InlineKeyboardMarkup:
    """Навигация для многошаговых визардов: [◀️ Назад] + [❌ Отмена]."""
    kb = InlineKeyboardBuilder()
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(
            text="◀️ Назад", callback_data="fsm_back", style="primary"
        ))
    row.append(InlineKeyboardButton(
        text="❌ Отмена", callback_data=f"fsm_cancel:{back_cb}", style="danger"
    ))
    kb.row(*row)
    return kb.as_markup()


# ── User menus ────────────────────────────────────────────────────────────────

def user_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Мой аккаунт", callback_data="my_account"))
    kb.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="close", style="primary"))
    return kb.as_markup()


def user_generic_back_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(*nav_row(home_cb="user_menu"))
    return kb.as_markup()


def photo_close_kb() -> InlineKeyboardMarkup:
    """Одна кнопка «Закрыть» для фото-сообщений (QR и т.п.)."""
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="close"))
    return kb.as_markup()


def photo_nav_kb(back_cb: str = None, home_cb: str = "menu") -> InlineKeyboardMarkup:
    """Навигация для фото-сообщений: [◀️ Назад] [🏠] [✕ Закрыть]."""
    kb = InlineKeyboardBuilder()
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()


def apps_kb(back_cb: str = "my_account", home_cb: str = "user_menu") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🤖 Hiddify Android", url="https://play.google.com/store/apps/details?id=app.hiddify.com"),
        InlineKeyboardButton(text="🍎 Hiddify iOS", url="https://apps.apple.com/app/id6596777532"),
    )
    kb.row(InlineKeyboardButton(
        text="💻 Hiddify Desktop (GitHub)",
        url="https://github.com/hiddify/hiddify-app/releases/latest",
    ))
    kb.row(
        InlineKeyboardButton(text="🤖 v2rayNG", url="https://github.com/2dust/v2rayNG/releases/latest"),
        InlineKeyboardButton(text="🍎 Streisand", url="https://apps.apple.com/app/id6450534064"),
    )
    kb.row(
        InlineKeyboardButton(text="🤖 NekoBox", url="https://github.com/MatsuriDayo/NekoBoxForAndroid/releases/latest"),
        InlineKeyboardButton(text="💻 Nekoray", url="https://github.com/MatsuriDayo/nekoray/releases/latest"),
    )
    kb.row(*nav_row(back_cb=back_cb, home_cb=home_cb))
    return kb.as_markup()
