from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from autocheck.common import DEFAULT_TIMEOUT, CheckinResult, cookie_headers


RAILGUN_BASE_URL = "https://railgun.info"
RAILGUN_DEFAULT_TOKEN = "railgun.info"


@dataclass
class RailgunAccountResult:
    ok: bool
    details: list[str]


def json_message(data: dict[str, Any]) -> str:
    message = data.get("message") or data.get("msg")
    return str(message) if message else str(data)


def code_ok(data: dict[str, Any]) -> bool:
    code = data.get("code")
    return code in (None, 0)


def checkin_ok(data: dict[str, Any]) -> bool:
    if code_ok(data):
        return True
    message = json_message(data).lower()
    return any(text in message for text in ("already", "repeat", "tomorrow", "已", "重复"))


def data_part(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("data")
    return value if isinstance(value, dict) else {}


def format_days(value: Any) -> str:
    try:
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def format_bytes(value: Any) -> str:
    try:
        size = float(value)
    except (TypeError, ValueError):
        return str(value)

    units = ("B", "KB", "MB", "GB", "TB", "PB")
    unit_index = 0
    while abs(size) >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}".rstrip("0").rstrip(".")


def first_value(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def nested_first_value(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    stack: list[Any] = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            found = first_value(item, keys)
            if found is not None:
                return found
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return None


def traffic_details(traffic: dict[str, Any], status: dict[str, Any]) -> list[str]:
    details: list[str] = []
    traffic_data = data_part(traffic)
    status_data = data_part(status)

    left = nested_first_value(
        {"traffic": traffic_data, "status": status_data},
        (
            "left",
            "leftTraffic",
            "trafficLeft",
            "remain",
            "remaining",
            "remainingTraffic",
            "available",
            "availableTraffic",
        ),
    )
    used = nested_first_value(
        {"traffic": traffic_data, "status": status_data},
        ("used", "usedTraffic", "trafficUsed", "usage", "usedBytes"),
    )
    total = nested_first_value(
        {"traffic": traffic_data, "status": status_data},
        ("total", "totalTraffic", "trafficTotal", "quota", "transfer", "budget"),
    )
    today = nested_first_value(traffic_data, ("today", "todayTraffic", "daily", "day"))

    if left is not None:
        details.append(f"剩余流量: {format_bytes(left)}")
    if total is not None:
        details.append(f"总流量: {format_bytes(total)}")
    if used is not None:
        details.append(f"已用流量: {format_bytes(used)}")
    if today is not None:
        details.append(f"今日已用流量: {format_bytes(today)}")

    if not details and traffic_data:
        visible_keys = ", ".join(sorted(str(key) for key in traffic_data.keys()))
        details.append(f"流量接口已返回，但未识别字段: {visible_keys}")
    return details


class RailgunTask:
    def __init__(self, cookie: str, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(cookie_headers(cookie, f"{self.base_url}/console/checkin"))
        self.session.headers.update(
            {
                "origin": self.base_url,
                "content-type": "application/json;charset=UTF-8",
            }
        )

    def request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=DEFAULT_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected response: {payload!r}")
        return payload

    def checkin(self) -> dict[str, Any]:
        return self.request_json(
            "POST",
            "/api/user/checkin",
            json={"token": self.token},
            headers={"referer": f"{self.base_url}/console/checkin"},
        )

    def status(self) -> dict[str, Any]:
        return self.request_json(
            "GET",
            "/api/user/status",
            headers={"referer": f"{self.base_url}/console/checkin"},
        )

    def traffic(self) -> dict[str, Any]:
        return self.request_json(
            "GET",
            "/api/user/traffic",
            headers={"referer": f"{self.base_url}/console"},
        )


def check_account(cookie: str, index: int, base_url: str, token: str) -> RailgunAccountResult:
    task = RailgunTask(cookie, base_url, token)
    details = [f"账号 {index}"]

    checkin = task.checkin()
    if not checkin_ok(checkin):
        return RailgunAccountResult(False, [*details, f"签到失败: {json_message(checkin)}"])
    details.append(f"签到结果: {json_message(checkin)}")

    status = task.status()
    if not code_ok(status):
        return RailgunAccountResult(False, [*details, f"状态查询失败: {json_message(status)}"])

    status_data = data_part(status)
    left_days = first_value(status_data, ("leftDays", "left_days", "days", "expireDays"))
    if left_days is not None:
        details.append(f"剩余天数: {format_days(left_days)} 天")

    plan = first_value(status_data, ("plan", "level", "vip", "package", "class"))
    if plan is not None:
        details.append(f"套餐/等级: {plan}")

    try:
        traffic = task.traffic()
        if code_ok(traffic):
            details.extend(traffic_details(traffic, status))
        else:
            details.append(f"流量查询失败: {json_message(traffic)}")
    except Exception as exc:
        details.append(f"流量查询异常: {exc}")

    return RailgunAccountResult(True, details)


def check_railgun(cookie_text: str, base_url: str = RAILGUN_BASE_URL, token: str = RAILGUN_DEFAULT_TOKEN) -> CheckinResult:
    cookies = [line.strip() for line in cookie_text.splitlines() if line.strip()]
    if not cookies:
        return CheckinResult("Railgun", False, "missing RAILGUN_COOKIE/GLADOS_COOKIE secret")

    account_results: list[RailgunAccountResult] = []
    for index, cookie in enumerate(cookies, start=1):
        try:
            account_results.append(check_account(cookie, index, base_url, token))
        except Exception as exc:
            account_results.append(RailgunAccountResult(False, [f"账号 {index}", f"请求异常: {exc}"]))

    ok = all(result.ok for result in account_results)
    details: list[str] = []
    for result in account_results:
        details.extend(result.details)
        details.append("")
    if details and details[-1] == "":
        details.pop()

    return CheckinResult(
        "Railgun",
        ok,
        "全部账号签到完成" if ok else "部分账号签到失败",
        details=details,
    )
