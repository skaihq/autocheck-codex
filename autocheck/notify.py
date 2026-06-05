from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from html import escape

import requests

from autocheck.common import DEFAULT_TIMEOUT, CheckinResult


def telegram_api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def env_value(env: dict[str, str], *names: str) -> str:
    for name in names:
        value = env.get(name, "").strip()
        if value:
            return value
    return ""


def clean_bot_token(token: str) -> str:
    marker = "HTTP API:"
    if marker in token:
        return token.split(marker, 1)[1].strip()
    return token


def today_text() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def first_match(details: list[str], pattern: str) -> str:
    for detail in details:
        match = re.search(pattern, detail)
        if match:
            return match.group(1)
    return ""


def clean_number(value: str) -> str:
    if value.endswith(".0"):
        return value[:-2]
    return value


def clean_size(value: str) -> str:
    return re.sub(r"\b([0-9]+)\.00\b", r"\1", value)


def format_bilibili(result: CheckinResult) -> list[str]:
    if not result.ok:
        return ["Bilibili", f"✗ {result.message}"]

    name = first_match(result.details, r"登录正常:\s*(.+)")
    suffix = f"（{name}）" if name else ""
    return ["Bilibili", f"✓ 签到成功{suffix}"]


def format_v2ex(result: CheckinResult) -> list[str]:
    if not result.ok:
        return ["V2EX", f"✗ {result.message}"]

    streak = first_match(result.details, r"已连续登录\s*(\d+)\s*天")
    reward = clean_number(first_match(result.details, r"今日/最近奖励:\s*([0-9.]+)\s*铜币"))
    balance = clean_number(first_match(result.details, r"当前余额:\s*([0-9.]+)\s*铜币"))

    status = f"✓ 已签到（连续 {streak} 天）" if streak else "✓ 已签到"
    money = f"💰 +{reward} 铜币｜余额 {balance}" if reward and balance else ""
    return ["V2EX", *[line for line in (status, money) if line]]


def format_railgun(result: CheckinResult) -> list[str]:
    if not result.ok:
        return ["Railgun", f"✗ {result.message}"]

    days = clean_number(first_match(result.details, r"剩余天数:\s*([0-9.]+)\s*天"))
    level = first_match(result.details, r"套餐/等级:\s*(.+)")
    traffic = clean_size(first_match(result.details, r"今日已用流量:\s*(.+)"))

    lines = ["Railgun", "✓ 签到成功"]
    if days or level:
        left = f"剩余 {days} 天" if days else ""
        plan = f"Lv.{level}" if level else ""
        lines.append("⏳ " + "｜".join(item for item in (left, plan) if item))
    if traffic:
        lines.append(f"📶 今日流量 {traffic}")
    return lines


def format_default(result: CheckinResult) -> list[str]:
    if result.skipped:
        return []
    mark = "✓" if result.ok else "✗"
    return [result.name, f"{mark} {result.message}"]


def summary_message(results: list[CheckinResult]) -> str:
    formatters = {
        "Bilibili": format_bilibili,
        "V2EX": format_v2ex,
        "Railgun": format_railgun,
    }

    groups: list[list[str]] = [[f"📅 {today_text()} 签到汇总"]]
    for result in results:
        lines = formatters.get(result.name, format_default)(result)
        if lines:
            groups.append(lines)

    return "\n\n".join("\n".join(group) for group in groups)


def send_telegram_summary(results: list[CheckinResult], env: dict[str, str]) -> bool:
    token = clean_bot_token(env_value(env, "TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"))
    chat_id = env_value(env, "TG_CHAT_ID", "TELEGRAM_CHAT_ID")
    channel_id = env_value(env, "TG_CHANNEL_ID", "TELEGRAM_CHANNEL_ID")
    target_chat_id = channel_id or chat_id

    if not token or not target_chat_id:
        print("[SKIP] telegram: missing TG_BOT_TOKEN and TG_CHANNEL_ID/TG_CHAT_ID")
        return True

    try:
        sent = requests.post(
            telegram_api_url(token, "sendMessage"),
            json={
                "chat_id": target_chat_id,
                "text": escape(summary_message(results)),
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

        print("[OK] telegram: summary sent")
        return True
    except Exception as exc:
        print(f"[FAIL] telegram: request failed: {type(exc).__name__}")
        return False
