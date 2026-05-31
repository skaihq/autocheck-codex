from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from html import escape

import requests


DEFAULT_TIMEOUT = 20
BILIBILI_SIGN_OFFLINE_CODES = {1}
BILIBILI_ALREADY_DONE_CODES = {-500, 1011040}


@dataclass
class CheckinResult:
    name: str
    ok: bool
    message: str
    skipped: bool = False


def cookie_headers(cookie: str, referer: str | None = None) -> dict[str, str]:
    headers = {
        "cookie": cookie,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if referer:
        headers["referer"] = referer
    return headers


def check_bilibili(cookie: str) -> CheckinResult:
    if not cookie:
        return CheckinResult("Bilibili", False, "missing BILIBILI_COOKIE secret")

    session = requests.Session()
    session.headers.update(cookie_headers(cookie, "https://live.bilibili.com/"))

    try:
        nav = session.get(
            "https://api.bilibili.com/x/web-interface/nav",
            timeout=DEFAULT_TIMEOUT,
        )
        nav.raise_for_status()
        nav_data = nav.json()
        if nav_data.get("code") != 0 or not nav_data.get("data", {}).get("isLogin"):
            return CheckinResult("Bilibili", False, f"login check failed: {nav_data}")

        response = session.get(
            "https://api.live.bilibili.com/xlive/web-ucenter/v1/sign/DoSign",
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return CheckinResult("Bilibili", False, f"request failed: {exc}")

    code = data.get("code")
    message = data.get("message") or data.get("msg") or str(data)
    if code == 0:
        return CheckinResult("Bilibili", True, message)
    if code in BILIBILI_ALREADY_DONE_CODES or "already" in message.lower():
        return CheckinResult("Bilibili", True, message)
    if code in BILIBILI_SIGN_OFFLINE_CODES:
        return CheckinResult("Bilibili", True, f"skipped: {message}", skipped=True)
    return CheckinResult("Bilibili", False, f"check-in failed: {data}")


def check_v2ex(cookie: str) -> CheckinResult:
    if not cookie:
        return CheckinResult("V2EX", False, "missing V2EX_COOKIE secret")

    session = requests.Session()
    session.headers.update(cookie_headers(cookie, "https://www.v2ex.com/mission/daily"))

    try:
        page = session.get(
            "https://www.v2ex.com/mission/daily",
            timeout=DEFAULT_TIMEOUT,
        )
        page.raise_for_status()
        html = page.text

        if "/signin" in page.url or "signout" not in html:
            return CheckinResult("V2EX", False, "login check failed")

        match = re.search(r"/mission/daily/redeem\?once=(\d+)", html)
        if not match:
            return CheckinResult("V2EX", True, "already checked in")

        redeem = session.get(
            f"https://www.v2ex.com/mission/daily/redeem?once={match.group(1)}",
            timeout=DEFAULT_TIMEOUT,
        )
        redeem.raise_for_status()

        verify = session.get(
            "https://www.v2ex.com/mission/daily",
            timeout=DEFAULT_TIMEOUT,
        )
        verify.raise_for_status()
        if not re.search(r"/mission/daily/redeem\?once=(\d+)", verify.text):
            return CheckinResult("V2EX", True, "checked in")
    except Exception as exc:
        return CheckinResult("V2EX", False, f"request failed: {exc}")

    return CheckinResult("V2EX", False, "check-in result could not be verified")


def telegram_api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def checkin_status_text(result: CheckinResult) -> str:
    return "成功打卡" if result.ok else "打卡失败"


def send_telegram_notification(results: list[CheckinResult]) -> bool:
    token = env_value("TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    chat_id = env_value("TG_CHAT_ID", "TELEGRAM_CHAT_ID")
    channel_id = env_value("TG_CHANNEL_ID", "TELEGRAM_CHANNEL_ID")
    target_chat_id = channel_id or chat_id

    if not token or not target_chat_id:
        print("[SKIP] telegram: missing TG_BOT_TOKEN and TG_CHANNEL_ID/TG_CHAT_ID")
        return True

    title = "自动打卡通知"
    lines = [f"<b>{escape(title)}</b>", ""]
    for result in results:
        status_text = checkin_status_text(result)
        lines.append(f"<b>{escape(result.name)}</b>：{escape(status_text)}")
        lines.append(f"原因：{escape(result.message)}")
        lines.append("")

    message = "\n".join(lines)
    try:
        sent = requests.post(
            telegram_api_url(token, "sendMessage"),
            json={
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        sent.raise_for_status()
        payload = sent.json()
        if not payload.get("ok"):
            print(f"[FAIL] telegram: sendMessage failed: {payload}")
            return False

        print("[OK] telegram: message sent")
        return True
    except Exception as exc:
        print(f"[FAIL] telegram: request failed: {exc}")
        return False


def main() -> int:
    checks = [
        check_bilibili(os.getenv("BILIBILI_COOKIE", "").strip()),
        check_v2ex(os.getenv("V2EX_COOKIE", "").strip()),
    ]

    failed = False
    for result in checks:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.message}")
        failed = failed or not result.ok

    notification_ok = send_telegram_notification(checks)

    return 1 if failed or not notification_ok else 0


if __name__ == "__main__":
    sys.exit(main())
