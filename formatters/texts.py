"""Static and lightly parametrised message texts shared by several handlers."""

from utils.html import esc

ADMIN_MENU = "👋 <b>Hiddify Admin</b>\n\nВыбери действие:"

APPS = (
    "📱 <b>Приложения для подключения</b>\n\n"
    "Нажми на приложение — скачаешь и настроишь через «Импорт подписки».\n\n"
    "<b>Hiddify</b> — рекомендуем, поддерживает все протоколы.\n"
    "<b>v2rayNG / NekoBox</b> — Android-альтернативы.\n"
    "<b>Streisand</b> — лучший выбор для iOS."
)


def link(sub_url: str) -> str:
    return (
        f"🔑 <b>Ссылка подписки</b>\n\n"
        f"<code>{esc(sub_url)}</code>\n\n"
        f"<i>Нажми на ссылку чтобы скопировать\n"
        f"или QR-код для сканирования</i>"
    )


def qr_caption(sub_url: str, title: str) -> str:
    return f"📲 <b>{title}</b>\n\nИли скопируй ссылку:\n<code>{esc(sub_url)}</code>"
