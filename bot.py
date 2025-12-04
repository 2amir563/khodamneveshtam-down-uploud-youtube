#!/usr/bin/env python3
"""
YouTube & Direct-Link Telegram Bot
Memory-Only Stream  |  systemd service  |  Port none (polling)
Repo: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube
"""
import os
import io
import logging
import requests
import mimetypes
from urllib.parse import urlparse
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import yt_dlp

load_dotenv()
TOKEN   = os.getenv("BOT_TOKEN")
OWNER   = int(os.getenv("OWNER_ID", 0))
MAXSIZE = 2_000_000_000          # 2 GB
CHUNK   = 512 * 1024             # 512 KB

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# ------------------ YouTube quality map ------------------
QUALITY_MAP = {
    "best":  {"format": "bestvideo+bestaudio/best",   "ext": "mp4"},
    "720":   {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]", "ext": "mp4"},
    "480":   {"format": "bestvideo[height<=480]+bestaudio/best[height<=480]", "ext": "mp4"},
    "audio": {"format": "bestaudio", "ext": "m4a"},
}

def quality_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 بهترین کیفیت", callback_data="best"),
         InlineKeyboardButton("⚙️ 720p", callback_data="720")],
        [InlineKeyboardButton("📱 480p", callback_data="480"),
         InlineKeyboardButton("🎧 فقط صدا", callback_data="audio")]
    ])

# ------------------ /start ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 لینک یوتیوب یا هر لینک دانلود مستقیم بفرستید…",
        reply_markup=quality_keyboard()
    )

# ------------------ YouTube (memory stream) ------------------
async def youtube_stream_upload(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                link: str, qual: str):
    opts = QUALITY_MAP[qual]
    ydl_opts = {
        "format": opts["format"],
        "outtmpl": "-",                 # pipe to stdout
        "quiet": True,
        "noplaylist": True,
    }
    buffer = io.BytesIO()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        title = info.get("title", "YouTube")
        ydl.download([link])
        buffer.seek(0)

    if buffer.getbuffer().nbytes > MAXSIZE:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="❌ فایل بزرگ‌تر از ۲ GB است.")
        buffer.close()
        return

    buffer.seek(0)
    filename = f"{info['id']}.{opts['ext']}"
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=buffer,
        filename=filename,
        caption=f"✅ {title}\n📥 کیفیت: {qual}",
        read_timeout=120, write_timeout=120, connect_timeout=120
    )
    buffer.close()

# ------------------ Direct link (stream) ------------------
async def direct_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return
    try:
        with requests.head(url, allow_redirects=True, timeout=10) as r:
            r.raise_for_status()
            size = int(r.headers.get("Content-Length", 0))
            if size > MAXSIZE:
                await update.message.reply_text("❌ فایل بزرگ‌تر از ۲ GB است.")
                return
        await update.message.reply_text("⬇️ در حال دریافت فایل …")
        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            ext = mimetypes.guess_extension(r.headers.get("Content-Type", "")) or ""
            filename = f"file{ext}"
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=r.iter_content(chunk_size=CHUNK),
                filename=filename,
                caption=f"✅ دانلود شد\n🔗 {url}",
                read_timeout=120, write_timeout=120, connect_timeout=120
            )
        await update.message.reply_text("✅ آپلود تمام شد.")
    except Exception as e:
        logging.error(e)
        await update.message.reply_text(f"❌ خطا در دانلود: {e}")

# ------------------ Callback (YouTube quality) ------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qual = query.data
    link = context.user_data.get("link")
    if not link:
        await query.edit_message_text("❌ ابتدا لینک یوتیوب بفرستید.")
        return
    await query.edit_message_text("⬇️ در حال دانلود …")
    await youtube_stream_upload(update, context, link, qual)

# ------------------ Routing ------------------
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    # YouTube
    application.add_handler(MessageHandler(filters.Regex(r"(youtube\.com|youtu\.be)") & ~filters.COMMAND, receive_link))
    # Direct link
    application.add_handler(MessageHandler(filters.Regex(r"^https?://") & ~filters.COMMAND, direct_download))
    # inline keyboard
    application.add_handler(CallbackQueryHandler(button))
    print("[*] Bot started (YouTube + Direct Download)")
    application.run_polling()

if __name__ == "__main__":
    main()
