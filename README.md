# Auto Check

一个简单的 GitHub Actions 自动签到项目。

支持：

- Bilibili
- V2EX
- Railgun
- Telegram 通知

## 目录

```text
autocheck/
├─ main.py
├─ common.py
├─ notify.py
└─ sites/
   ├─ bilibili.py
   ├─ v2ex.py
   └─ railgun.py
```

说明：

- `main.py`：程序入口。
- `common.py`：公共结果模型、请求头、超时设置。
- `notify.py`：Telegram 汇总通知。
- `sites/`：各个平台的签到逻辑。
- `tests/`：仅用于开发测试，打包时不包含。

## 使用

在 GitHub 仓库里添加这些 Secrets：

```text
BILIBILI_COOKIE
V2EX_COOKIE
RAILGUN_COOKIE
RAILGUN_BASE_URL
RAILGUN_TOKEN
TG_BOT_TOKEN
TG_CHAT_ID
TG_CHANNEL_ID
```

兼容旧变量：

```text
GLADOS
GLADOS_COOKIE
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
TELEGRAM_CHANNEL_ID
```

运行：

```bash
python -m autocheck.main
```

## 打包

`pyproject.toml` 只包含 `autocheck*` 包，不包含 `tests*`。

真实 Cookie 只应该放在 GitHub Secrets 或本地测试环境变量里，不要写进代码。

## 通知格式

Telegram 会发送一条汇总消息：

```text
📅 2026-06-05 签到汇总

Bilibili
✓ 签到成功（用户名）

V2EX
✓ 已签到（连续 300 天）
💰 +3 铜币｜余额 4017

Railgun
✓ 签到成功
⏳ 剩余 200 天｜Lv.21
📶 今日流量 0 B
```
