"""Statistics and node screens built from the panel's dashboard and nodes data."""

from utils.html import esc
from utils.types import JsonDict

_SPARK = "▁▂▃▄▅▆▇█"
_STATUS_ICONS = {"online": "🟢", "late": "🟡", "offline": "🔴", "never": "⚪"}
_KB = 1024
_MB = _KB**2
_GB = _KB**3


def size(num_bytes: float) -> str:
    """Human-readable byte count: GB, MB or KB."""
    if num_bytes >= _GB:
        return f"{num_bytes / _GB:.2f} GB"
    if num_bytes >= _MB:
        return f"{num_bytes / _MB:.1f} MB"
    return f"{num_bytes / _KB:.0f} KB"


def _trend(percent: float | None) -> str:
    if percent is None:
        return ""
    return f" ▲{percent:.0f}%" if percent >= 0 else f" ▼{abs(percent):.0f}%"


def sparkline(values: list[int]) -> str:
    """One block character per value, scaled to the largest."""
    top = max(values, default=0)
    if top <= 0:
        return _SPARK[0] * len(values)
    return "".join(_SPARK[round(v / top * (len(_SPARK) - 1))] for v in values)


def stats_card(data: JsonDict) -> str:
    users = data.get("users", {})
    online = users.get("online", {})
    usage = data.get("usage", {})
    totals = usage.get("totals", {})
    trends = usage.get("trends", {})
    series = data.get("series", [])
    days = len(series)

    lines = [
        "📈 <b>Статистика</b>",
        "",
        f"👥 Пользователей: <b>{users.get('total', 0)}</b> (включено {users.get('enabled', 0)})",
        f"🟢 Онлайн: сейчас <b>{online.get('m5', 0)}</b> · за сутки <b>{online.get('h24', 0)}</b>"
        f" · сегодня <b>{online.get('today', 0)}</b>",
        "",
        "📦 <b>Трафик</b>",
        f"  Сегодня: <b>{size(totals.get('today', 0))}</b>{_trend(trends.get('day'))}",
        f"  Вчера: {size(totals.get('yesterday', 0))}",
        f"  7 дней: <b>{size(totals.get('week', 0))}</b>{_trend(trends.get('week'))}",
        f"  30 дней: <b>{size(totals.get('month', 0))}</b>{_trend(trends.get('month'))}",
        f"  Всего: {size(totals.get('total', 0))}",
    ]
    if average := usage.get("averages", {}).get("daily_month"):
        lines.append(f"📊 В среднем за день (30 дн.): {size(average)}")
    if peak := usage.get("peak"):
        lines.append(f"🏔 Пик: {size(peak.get('usage', 0))} ({esc(peak.get('date'))})")
    if series:
        lines += [
            "",
            f"<code>{sparkline([p.get('usage', 0) for p in series])}</code>",
            f"последние {days} дн.",
        ]
    return "\n".join(lines)


def nodes_text(nodes: list[JsonDict]) -> str:
    """Node overview; never include `admin_url`, it embeds the admin's secret uuid."""
    lines = [f"🌐 <b>Серверы (узлы)</b>: {len(nodes)}", ""]
    for node in nodes:
        icon = _STATUS_ICONS.get(str(node.get("status")), "⚪")
        details = node.get("details", {})
        lines.append(f"{icon} <b>{esc(node.get('name'))}</b> · {esc(node.get('host')) or '—'}")
        lines.append(
            f"   сегодня: {size(details.get('today_usage', 0))}, онлайн {details.get('today_online', 0)}"
        )
        if domains := node.get("domains"):
            lines.append(f"   домены: {esc(', '.join(domains))}")
    return "\n".join(lines)
