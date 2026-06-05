from __future__ import annotations

import os
import sys

from autocheck.common import CheckinResult
from autocheck.notify import send_telegram_summary
from autocheck.sites.bilibili import check_bilibili
from autocheck.sites.railgun import RAILGUN_BASE_URL, RAILGUN_DEFAULT_TOKEN, check_railgun
from autocheck.sites.v2ex import check_v2ex


def env_value(env: dict[str, str], *names: str) -> str:
    for name in names:
        value = env.get(name, "").strip()
        if value:
            return value
    return ""


def skipped(name: str, secret: str) -> CheckinResult:
    return CheckinResult(name, True, f"missing {secret}, skipped", skipped=True)


def print_result(result: CheckinResult) -> None:
    status = "SKIP" if result.skipped else "OK" if result.ok else "FAIL"
    print(f"[{status}] {result.name}: {result.message}")
    for detail in result.details:
        print(f"  - {detail}")


def main() -> int:
    env = dict(os.environ)
    bilibili_cookie = env_value(env, "BILIBILI_COOKIE")
    v2ex_cookie = env_value(env, "V2EX_COOKIE")
    railgun_cookie = env_value(env, "RAILGUN_COOKIE", "GLADOS_COOKIE", "GLADOS")

    checks = [
        check_bilibili(bilibili_cookie)
        if bilibili_cookie
        else skipped("Bilibili", "BILIBILI_COOKIE"),
        check_v2ex(v2ex_cookie)
        if v2ex_cookie
        else skipped("V2EX", "V2EX_COOKIE"),
        check_railgun(
            railgun_cookie,
            env_value(env, "RAILGUN_BASE_URL") or RAILGUN_BASE_URL,
            env_value(env, "RAILGUN_TOKEN") or RAILGUN_DEFAULT_TOKEN,
        )
        if railgun_cookie
        else skipped("Railgun", "RAILGUN_COOKIE"),
    ]

    failed = False
    for result in checks:
        print_result(result)
        failed = failed or not result.ok

    notification_failed = not send_telegram_summary(checks, env)

    return 1 if failed or notification_failed else 0


if __name__ == "__main__":
    sys.exit(main())
