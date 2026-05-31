# GitHub Actions Auto Check-in

This repository contains a GitHub Actions workflow for bilibili live check-in
and the V2EX daily mission reward.

## Usage

1. Push these files to a GitHub repository.
2. Open `Settings` -> `Secrets and variables` -> `Actions`.
3. Add these Repository secrets:
   - `BILIBILI_COOKIE`: the full Cookie header from a logged-in bilibili request.
   - `V2EX_COOKIE`: the full Cookie header from a logged-in V2EX request.
   - `TG_BOT_TOKEN`: the token from BotFather.
   - `TG_CHAT_ID`: the chat ID that receives the first bot message.
   - `TG_CHANNEL_ID`: optional channel ID or `@channel_username` to forward
     the bot message to a channel.
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `TELEGRAM_CHANNEL_ID` are
     also supported as aliases.
4. Open `Actions` -> `Auto Check-in` to run it manually, or wait for the schedule.

The default schedule runs at 01:15 UTC every day, which is 09:15 in Beijing
time. Edit the cron expression in `.github/workflows/auto-checkin.yml` if you
want a different time.

## Notes

- Cookies are login credentials. Store them only in GitHub Secrets.
- The script does not bypass captcha, two-factor checks, or anti-abuse systems.
- If either website changes its API or page structure, the script may need an
  update.
- To forward to a Telegram channel, add the bot to that channel as an admin with
  permission to post messages.
- bilibili currently returns `签到活动已下线，无法使用。` for the old live check-in
  endpoint. The workflow treats that response as a skipped success so V2EX and
  Telegram notifications can still complete.
