#!/usr/bin/env python3
"""Telegram HTML cleanup/decoder bot. Does not execute uploaded JavaScript."""
import ast
import base64
import binascii
import html
import logging
import os
import re
from io import BytesIO

from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024


def decode_common_escapes(text: str) -> str:
    # Decode JS-style \xNN and \uNNNN escapes in text without executing code.
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    return text


def maybe_decode_base64(text: str) -> str:
    # Only decode whole quoted Base64-looking strings when the result is printable UTF-8.
    pattern = re.compile(r"""(['"])([A-Za-z0-9+/]{24,}={0,2})\1""")

    def replace(match):
        value = match.group(2)
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return match.group(0)
        if not decoded or sum(ch.isprintable() or ch in "\r\n\t" for ch in decoded) / len(decoded) < 0.95:
            return match.group(0)
        return match.group(1) + decoded.replace("\\", "\\\\").replace(match.group(1), "\\" + match.group(1)) + match.group(1)

    return pattern.sub(replace, text)


def clean_html(source: str) -> str:
    source = decode_common_escapes(source)
    source = maybe_decode_base64(source)
    soup = BeautifulSoup(source, "html.parser")
    # Format HTML. Script contents are not executed.
    pretty = soup.prettify()
    try:
        import jsbeautifier
        for script in soup.find_all("script"):
            if script.string and script.string.strip():
                try:
                    script.string.replace_with(jsbeautifier.beautify(script.string))
                except Exception:
                    pass
        pretty = soup.prettify()
    except ImportError:
        pass
    return pretty


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "👋 HTML Decoder Bot চালু আছে।\n\n"
        "একটি .html বা .htm ফাইল পাঠাও। আমি HTML format/cleanup এবং কিছু সাধারণ "
        "escape/Base64 decoding চেষ্টা করব।\n"
        "সতর্কতা: সব ধরনের custom obfuscation বা encryption decode করা সম্ভব নয়।"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    doc = message.document
    if not doc:
        return
    filename = doc.file_name or "upload.html"
    if not filename.lower().endswith((".html", ".htm")):
        await message.reply_text("শুধু .html বা .htm ফাইল পাঠাও।")
        return
    if doc.file_size and doc.file_size > MAX_BYTES:
        await message.reply_text("ফাইলটি 5 MB-এর বেশি। ছোট HTML ফাইল পাঠাও।")
        return
    try:
        tg_file = await doc.get_file()
        buffer = BytesIO()
        await tg_file.download_to_memory(out=buffer)
        raw = buffer.getvalue()
        if len(raw) > MAX_BYTES:
            await message.reply_text("ফাইলটি 5 MB-এর বেশি।")
            return
        source = raw.decode("utf-8", errors="replace")
        result = clean_html(source).encode("utf-8")
        output = BytesIO(result)
        output.name = "cleaned_output.html"
        await message.reply_document(
            document=output,
            filename="cleaned_output.html",
            caption="✅ HTML cleanup complete. JavaScript execute করা হয়নি।",
        )
    except Exception:
        log.exception("Failed to process uploaded HTML")
        await message.reply_text("ফাইল প্রসেস করা যায়নি। HTML ফাইলটি পরীক্ষা করে আবার পাঠাও।")


def main() -> None:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is missing. Set it in Render Environment.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    log.info("Starting Telegram HTML Decoder Bot polling")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
