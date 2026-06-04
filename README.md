# GitHub Actions Auto Check-in

This repository contains a GitHub Actions workflow for bilibili daily tasks,
the V2EX daily mission reward, Railgun check-in, and FN NAS community check-in.

hello

## Usage

1. Push these files to a GitHub repository.
2. Open `Settings` -> `Secrets and variables` -> `Actions`.
3. Add these Repository secrets:
   - `BILIBILI_COOKIE`: the full Cookie header from a logged-in bilibili request.
   - `V2EX_COOKIE`: the full Cookie header from a logged-in V2EX request.
   - `RAILGUN_COOKIE`: the full Cookie header from a logged-in Railgun request.
     Multiple Railgun accounts can be added as multiple lines in this secret.
   - `RAILGUN_BASE_URL`: optional, defaults to `https://railgun.info`.
   - `RAILGUN_TOKEN`: optional, defaults to `railgun.info`.
   - `GLADOS`, `GLADOS_COOKIE`: legacy aliases for `RAILGUN_COOKIE`.
   - `FNNAS_COOKIE`: the full Cookie header from a logged-in
     `https://club.fnnas.com/` request.
   - `FNNAS_SIGN_DATA`: optional single FN NAS direct sign-in secret. Put three
     lines in one secret: `saltkey`, `auth`, then `sign`.
   - `fn_pvRK_2132_saltkey`, `fn_pvRK_2132_auth`, `fn_pvRK_2132_sign`:
     optional FN NAS direct sign-in secrets. When all three are present, the
     workflow uses the direct sign URL mode from the FN_AQ-style script instead
     of discovering the sign parameter from the page.
   - `TG_BOT_TOKEN`: the token from BotFather.
   - `TG_CHANNEL_ID`: the channel ID or `@channel_username` that receives the
     Telegram message.
   - `TG_CHAT_ID`: optional fallback chat ID if `TG_CHANNEL_ID` is not set.
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `TELEGRAM_CHANNEL_ID` are
     also supported as aliases.
4. Open `Actions` -> `Auto Check-in` to run it manually, or wait for the schedule.

Example `FNNAS_SIGN_DATA` value:

```text
R722ok73
76f7...
your_sign_value
```

The default schedule runs at 01:15 UTC every day, which is 09:15 in Beijing
time. Edit the cron expression in `.github/workflows/auto-checkin.yml` if you
want a different time.

## Notes

- Cookies are login credentials. Store them only in GitHub Secrets.
- The script does not bypass captcha, two-factor checks, or anti-abuse systems.
- If either website changes its API or page structure, the script may need an
  update.
- To send to a Telegram channel, add the bot to that channel as an admin with
  permission to post messages. `TG_BOT_TOKEN` + `TG_CHANNEL_ID` is enough.
- Bilibili runs login verification, video watch heartbeat, video sharing,
  one-coin voting, live sign-in, and manga sign-in. The one-coin task consumes
  one coin when a suitable uncoined video is found.
- If bilibili returns that an older live sign-in endpoint is offline, the
  workflow treats that response as a skipped success so V2EX and Telegram
  notifications can still complete.
- V2EX checks the daily mission page, redeems the daily reward when available,
  then reads `/balance` to report the reward amount, current total balance, and
  latest balance record.
- Railgun uses `https://railgun.info` by default and calls `/api/user/checkin`,
  `/api/user/status`, and `/api/user/traffic`. Notifications include sign-in
  result, remaining days, plan level, and traffic details when the API returns
  recognizable fields.
- FN NAS community uses `https://club.fnnas.com/plugin.php?id=zqlj_sign`,
  checks the current sign-in button, and calls the sign URL when today's
  check-in is still available. It also supports direct `saltkey/auth/sign`
  secrets for setups where page login detection fails.
- Telegram notifications are sent separately for each service, so Bilibili,
  V2EX, Railgun, and FN NAS community have independent message titles and
  details.

## Script layout

- `scripts/checkin.py`: GitHub Actions entrypoint.
- `scripts/bilibili.py`: Bilibili login, watch, share, coin, live sign-in, and
  manga sign-in tasks.
- `scripts/v2ex.py`: V2EX daily mission and balance parsing.
- `scripts/railgun.py`: Railgun check-in, remaining days, and traffic parsing.
- `scripts/fnnas.py`: FN NAS community Cookie check-in.
- `scripts/notify.py`: Telegram notification sending.
- `scripts/common.py`: shared result model and HTTP defaults.
