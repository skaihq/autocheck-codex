from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

import requests

from common import DEFAULT_TIMEOUT, CheckinResult, cookie_headers


FNNAS_BASE_URL = "https://club.fnnas.com/"
FNNAS_SIGN_URL = urljoin(FNNAS_BASE_URL, "plugin.php?id=zqlj_sign")


def strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def parse_sign_button(html: str) -> tuple[str | None, str | None]:
    button_match = re.search(
        r"""<[^>]*class=["'][^"']*\bsignbtn\b[^"']*["'][^>]*>.*?<a\b([^>]*)>(.*?)</a>""",
        html,
        flags=re.S | re.I,
    )
    if not button_match:
        button_match = re.search(
            r"""<a\b([^>]*)class=["'][^"']*\bbtna\b[^"']*["'][^>]*>(.*?)</a>""",
            html,
            flags=re.S | re.I,
        )

    if not button_match:
        return None, None

    attrs, label_html = button_match.groups()
    text = strip_tags(label_html)
    href_match = re.search(r"""href=["']([^"']+)["']""", attrs, flags=re.I)
    href = unescape(href_match.group(1)) if href_match else ""
    sign_match = re.search(r"[?&]sign=([^&\"']+)", href)
    return text, sign_match.group(1) if sign_match else None


def parse_sign_info(html: str) -> list[str]:
    text = strip_tags(html)
    details: list[str] = []
    patterns = [
        r"最近打卡时间[:：]\s*[^ ]+",
        r"本月打卡天数[:：]\s*\d+\s*天?",
        r"连续打卡天数[:：]\s*\d+\s*天?",
        r"累计打卡天数[:：]\s*\d+\s*天?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            details.append(match.group(0))

    return details


def page_looks_logged_out(html: str, final_url: str) -> bool:
    return (
        "member.php?mod=logging&action=login" in final_url
        or "member.php?mod=logging&action=login" in html
        or "登录" in strip_tags(html) and "退出" not in strip_tags(html)
    )


class FNNASCheckin:
    def __init__(self, cookie: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(cookie_headers(cookie, FNNAS_SIGN_URL))
        self.session.headers.update(
            {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

    def sign_page(self) -> tuple[str, str]:
        response = self.session.get(FNNAS_SIGN_URL, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.text, response.url

    def do_sign(self, sign_param: str) -> None:
        response = self.session.get(
            f"{FNNAS_SIGN_URL}&sign={sign_param}",
            headers={"referer": FNNAS_SIGN_URL},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()


def check_fnnas(cookie: str) -> CheckinResult:
    if not cookie:
        return CheckinResult("飞牛社区", False, "missing FNNAS_COOKIE secret")

    task = FNNASCheckin(cookie)
    details: list[str] = []

    try:
        html, page_url = task.sign_page()
        if page_looks_logged_out(html, page_url):
            return CheckinResult("飞牛社区", False, "login check failed")

        sign_text, sign_param = parse_sign_button(html)
        if sign_text:
            details.append(f"当前状态: {sign_text}")
        details.extend(parse_sign_info(html))

        if sign_text and "已" in sign_text and ("打卡" in sign_text or "签到" in sign_text):
            return CheckinResult("飞牛社区", True, "今日已签到", details=details)

        if not sign_param:
            return CheckinResult("飞牛社区", False, "未找到签到按钮或 sign 参数", details=details)

        task.do_sign(sign_param)
        verify_html, verify_url = task.sign_page()
        if page_looks_logged_out(verify_html, verify_url):
            return CheckinResult("飞牛社区", False, "签到后登录状态失效", details=details)

        verify_text, _ = parse_sign_button(verify_html)
        verify_details = parse_sign_info(verify_html)
        if verify_text:
            details.append(f"签到后状态: {verify_text}")
        details.extend(item for item in verify_details if item not in details)

        if verify_text and "已" in verify_text and ("打卡" in verify_text or "签到" in verify_text):
            return CheckinResult("飞牛社区", True, "签到成功", details=details)

        return CheckinResult("飞牛社区", False, "签到请求已发送，但未验证到已签到状态", details=details)
    except requests.RequestException as exc:
        return CheckinResult("飞牛社区", False, f"request failed: {exc}", details=details)
    except Exception as exc:
        return CheckinResult("飞牛社区", False, f"check failed: {exc}", details=details)
