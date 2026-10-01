from utils.html import esc as _esc

_MODE_LABELS = {
    "no_reset": "без сброса",
    "monthly": "ежемесячно",
    "weekly": "еженедельно",
    "daily": "ежедневно",
}


def _fmt_online(val: str | None) -> str:
    if not val or str(val).startswith("0001"):
        return "никогда"
    return _esc(val)


def _fmt_date(val: str | None) -> str:
    """ISO 2024-01-15 → 15.01.2024"""
    if not val:
        return "—"
    try:
        y, m, d = val[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return _esc(val)


def user_card(u: dict) -> str:
    """Карточка пользователя для администратора."""
    used = u.get("current_usage_GB") or 0.0
    limit = u.get("usage_limit_GB") or 0.0
    days = u.get("package_days") or 0
    mode = u.get("mode") or "no_reset"
    active = u.get("is_active", False)
    enabled = u.get("enable", False)

    if limit == 0:
        status = "⛔ Заблокирован"
    elif active:
        status = "✅ Активен"
    elif enabled:
        status = "🟡 Включён"
    else:
        status = "⛔ Отключён"

    pct = (used / limit * 100) if limit else 0
    filled = min(10, round(pct / 10))
    bar = "▓" * filled + "░" * (10 - filled)

    lines = [
        f"👤 <b>{_esc(u.get('name')) or '—'}</b>  ·  {status}",
        f"<code>{_esc(u.get('uuid', '—'))}</code>",
        "",
        f"{bar}  {pct:.0f}%",
        f"📊  {used:.2f} / {limit:.1f} GB",
        "",
        f"📅  {days} дн.  ·  {_MODE_LABELS.get(mode, mode)}",
        f"🗓  Начало: {_fmt_date(u.get('start_date'))}",
        f"🕐  Онлайн: {_fmt_online(u.get('last_online'))}",
        f"🔗  Telegram: {u.get('telegram_id') or '—'}",
    ]
    if comment := u.get("comment"):
        lines.append(f"💬  {_esc(comment)}")

    return "\n".join(lines)


def account_card(data: dict) -> str:
    """Карточка для самого пользователя."""
    used = data["used"]
    total = data["total"]
    pct = (used / total * 100) if total else 0
    filled = min(10, round(pct / 10))
    bar = "▓" * filled + "░" * (10 - filled)
    days = data["days_left"]

    if days == 0:
        days_text = "⚠️ <b>истёк</b>"
    elif days <= 3:
        days_text = f"⚠️ <b>{days} дн.</b> — скоро истечёт!"
    else:
        days_text = f"<b>{days} дн.</b>"

    mode = _MODE_LABELS.get(data.get("mode", ""), data.get("mode", ""))
    expiry = data.get("expiry_date") or "—"
    last_online = _fmt_online(data.get("last_online"))

    lines = [
        f"👤 <b>{_esc(data['name'])}</b>",
        "",
        f"{bar}  {pct:.0f}%",
        f"📊  {used:.2f} / {total:.1f} GB",
        "",
        f"⏳  Осталось: {days_text}",
        f"📅  Истекает: {_esc(expiry) if expiry != '—' else '—'}",
        f"🔄  Сброс: {mode}",
        f"🕐  Онлайн: {last_online}",
    ]
    return "\n".join(lines)
