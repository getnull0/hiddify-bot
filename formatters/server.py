from utils.html import esc as _esc
from utils.types import JsonDict


def server_status(data: JsonDict) -> str:
    stats = data.get("stats", data)  # supports both nested and flat payloads
    s = stats.get("system", {})
    top5 = stats.get("top5", {})
    hist = data.get("usage_history", {})

    cpu = s.get("cpu_percent", 0)
    ram_used = s.get("ram_used", 0)
    ram_total = s.get("ram_total", 0)
    ram_pct = (ram_used / ram_total * 100) if ram_total else 0
    disk_used = s.get("disk_used", 0)
    disk_total = s.get("disk_total", 0)
    disk_pct = (disk_used / disk_total * 100) if disk_total else 0
    load1 = s.get("load_avg_1min", 0)
    load5 = s.get("load_avg_5min", 0)
    load15 = s.get("load_avg_15min", 0)
    conns = s.get("total_connections", 0)
    ips = s.get("total_unique_ips", 0)
    net_total = s.get("net_total_cumulative_GB", 0)

    lines = [
        "📊 <b>Статус сервера</b>",
        "",
        f"🖥 CPU: <b>{cpu:.1f}%</b>   Load (1/5/15): {load1:.2f} {load5:.2f} {load15:.2f}",
        f"🧠 RAM: <b>{ram_used:.2f} / {ram_total:.2f} GB</b>  ({ram_pct:.0f}%)",
        f"💾 Диск: <b>{disk_used:.2f} / {disk_total:.2f} GB</b>  ({disk_pct:.0f}%)",
        f"🌐 Сеть (накопленный): <b>{net_total:.1f} GB</b>",
        f"🔗 Соединений: <b>{conns}</b>   IP: <b>{ips}</b>",
    ]

    if hist:
        total = hist.get("total", {})
        today = hist.get("today", {})
        users = total.get("users", "—")
        today_gb = int(today.get("usage", 0) or 0) / 1024**3
        total_gb = int(total.get("usage", 0) or 0) / 1024**3
        online = total.get("online", "—")
        lines += [
            "",
            f"👥 Пользователей: <b>{users}</b>   Онлайн: <b>{online}</b>",
            f"📈 Сегодня: <b>{today_gb:.2f} GB</b>   Всего: <b>{total_gb:.2f} GB</b>",
        ]

    cpu_top = top5.get("cpu", [])
    if cpu_top:
        lines.append("")
        lines.append("⚡ <b>CPU топ-5:</b>")
        for name, pct in cpu_top[:5]:
            lines.append(f"  {_esc(name)}: {pct:.1f}%")

    return "\n".join(lines)


def panel_info(data: JsonDict) -> str:
    return (
        f"ℹ️ <b>Hiddify Panel</b>\n\n"
        f"Версия: <b>{_esc(data['version'])}</b>\n"
        f"Админ: {_esc(data['admin_name'])} ({_esc(data['admin_mode'])})"
    )
