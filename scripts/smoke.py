"""Smoke test of your real panel with the settings from .env (read-only unless --write)."""

import asyncio
import sys
import time
from http import HTTPStatus

import aiohttp

from hiddify_bot.api.client import API_ERRORS, HiddifyClient, describe_api_error
from hiddify_bot.config import HIDDIFY_URL, HIDDIFY_USER_PATH, settings


class Report:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.failures += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} {label}" + (f": {detail}" if detail else ""))


async def check_subscription_link(report: Report, uuid: str) -> None:
    url = f"{HIDDIFY_URL}/{HIDDIFY_USER_PATH}/{uuid}/"
    timeout = aiohttp.ClientTimeout(total=30)
    async with (
        aiohttp.ClientSession(timeout=timeout) as session,
        session.get(url, ssl=settings.verify_ssl, allow_redirects=False) as resp,
    ):
        status = resp.status
    hint = {
        int(HTTPStatus.BAD_REQUEST): "HIDDIFY_USER_PATH неверный (нужен клиентский путь)",
        int(HTTPStatus.FOUND): "панель не знает такого пользователя",
    }.get(status, "")
    report.check(status == HTTPStatus.OK, "ссылка подписки открывается", hint or f"HTTP {status}")


async def check_profile(client: HiddifyClient, uuid: str) -> None:
    try:
        profile = await client.get_user_profile(uuid)
    except API_ERRORS as exc:
        print(
            f"INFO профиль пользователя недоступен ({describe_api_error(exc)}): без дней до сброса"
        )
        return
    proxy = "включён" if profile.get("telegram_proxy_enable") else "выключен"
    print(
        f"OK   профиль пользователя: до сброса {profile.get('profile_reset_days')} дн., прокси Telegram {proxy}"
    )


async def read_only_checks(client: HiddifyClient, report: Report) -> None:
    me = await client.get_me()
    is_super = me.get("mode") == "super_admin"
    report.check(True, "доступ к панели", f"админ {me.get('name')} ({me.get('mode')})")
    report.check(
        is_super, "права super_admin", "" if is_super else "логи и обновление трафика не заработают"
    )
    info = await client.get_panel_info()
    report.check(True, "версия панели", str(info.get("version")))
    users = await client.list_users()
    report.check(True, "список пользователей", f"{len(users)} шт.")
    status = await client.get_server_status()
    report.check("system" in status.get("stats", {}), "статус сервера")
    if users:
        await check_subscription_link(report, users[0]["uuid"])
        await check_profile(client, users[0]["uuid"])
    else:
        print("INFO пользователей нет: проверка ссылки подписки пропущена (запусти с --write)")


async def write_checks(client: HiddifyClient, report: Report) -> None:
    created = await client.create_user(f"bot-smoke-{int(time.time())}", days=1, limit_gb=1)
    uuid = created["uuid"]
    try:
        report.check(created["is_active"], "создание пользователя")
        blocked = await client.update_user(uuid, enable=False)
        report.check(not blocked["is_active"], "блокировка (enable=False)")
        unblocked = await client.update_user(uuid, enable=True)
        report.check(unblocked["is_active"], "разблокировка")
        extended = await client.extend_user(uuid, 5)
        report.check(extended["package_days"] == 6, "продление", f"{extended['package_days']} дн.")
        reset = await client.reset_user_traffic(uuid)
        report.check(reset["current_usage_GB"] == 0, "сброс трафика")
        await check_subscription_link(report, uuid)
    finally:
        await client.delete_user(uuid)
        report.check(True, "тестовый пользователь удалён")


async def main(write: bool) -> int:
    report = Report()
    client = HiddifyClient(settings)
    try:
        await read_only_checks(client, report)
        if write:
            await write_checks(client, report)
    except API_ERRORS as exc:
        report.check(False, "запрос к панели", describe_api_error(exc))
    finally:
        await client.close()
    print("\nВсё в порядке." if not report.failures else f"\nПроблем: {report.failures}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--write" in sys.argv[1:])))
