# Telegram HTML Decoder Bot — Render deployment

## GitHub upload
Upload all five files from this folder to the root of your GitHub repository:
- `telegram_html_decoder_bot.py`
- `requirements.txt`
- `.python-version`
- `render.yaml`
- `README.md`

Make sure GitHub shows the dotfile `.python-version`. Its contents should be `3.12.10`.

## Render
1. Create a Blueprint from the connected repository, or create a Background Worker.
2. Set environment variable `BOT_TOKEN` to the token from Telegram's official @BotFather.
3. Deploy and inspect logs.
4. In Telegram, send `/start`, then upload an `.html` or `.htm` file (max 5 MB).

Start command: `python telegram_html_decoder_bot.py`

Important:
- Never commit your Telegram token to GitHub.
- Render Background Workers generally require a paid plan.
- The bot statically formats HTML and attempts common escape/Base64 cleanup. It does not execute JavaScript and cannot guarantee decoding of every obfuscation or encryption method.
