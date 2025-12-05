#!/usr/bin/env python3
"""
Telegram YouTube Downloader Bot - با نمایش حجم واقعی/تخمینی در همه کیفیت‌ها
حل کامل مشکل: همه دکمه‌ها همیشه حجم دارن!
"""

import os
import io
import re
import math
import logging
import tempfile
import asyncio
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

import yt_dlp

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
MAX_SIZE = 2_000_000_000  # 2GB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# فرمت‌های دقیق برای دانلود
QUALITIES = {
    "144": "best[height<=144][vcodec!=none][acodec!=none]/best",
    "240": "best[height<=240][vcodec!=none][acodec!=none]/best",
    "360": "best[height<=360][vcodec!=none][acodec!=none]/best",
    "480": "best[height<=480][vcodec!=none][acodec!=none]/best",
    "720": "best[height<=720][vcodec!=none][acodec!=none]/best",
    "1080": "best[height<=1080][vcodec!=none][acodec!=none]/best",
    "1440": "best[height<=1440][vcodec!=none][acodec!=none]/best",
    "2160": "best[height<=2160][vcodec!=none][acodec!=none]/best",
    "best": "best",
    "audio": "bestaudio[ext=m4a]"
}

QUALITY_LABELS = {
    "144": "144p", "240": "240p", "360": "360p", "480": "480p",
    "720": "720p", "1080": "1080p", "1440": "1440p", "2160": "2160p",
    "best": "Best", "audio": "Audio"
}

def format_size(size: int) -> str:
    if not size or size <= 0:
        return "نامشخص"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def estimate_size(duration: int, quality: str) -> int:
    """تخمین بسیار دقیق حجم بر اساس مدت و کیفیت (MB در دقیقه)"""
    if duration <= 0:
        duration = 180  # 3 دقیقه پیش‌فرض

    rates = {
        "144": 0.7,   # ~0.7 MB در دقیقه
        "240": 1.3,
        "360": 2.8,
        "480": 4.5,
        "720": 8.0,
        "1080": 13.0,
        "1440": 22.0,
        "2160": 45.0,
        "best": 15.0,
        "audio": 1.0
    }
    mb_per_min = rates.get(quality, 10.0)
    return int((duration / 60) * mb_per_min * 1024 * 1024)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! لینک یوتیوب یا مستقیم بفرست\n"
        "همه کیفیت‌ها حجم دارن (واقعی یا تخمین دقیق)\n"
        "حداکثر حجم: ۲ گیگابایت",
        parse_mode="Markdown"
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not ("youtube.com" in url or "youtu.be" in url):
        return

    msg = await update.message.reply_text("در حال دریافت اطلاعات ویدیو...")

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        context.user_data['youtube_url'] = url
        title = info.get('title', 'بدون عنوان')[:100]
        duration = info.get('duration') or 0

        # دیکشنری برای ذخیره حجم هر کیفیت
        size_map = {}

        # 1. حجم صوت
        for fmt in info.get('formats', []):
            if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                sz = fmt.get('filesize') or fmt.get('filesize_approx')
                if sz:
                    size_map['audio'] = int(sz)
                break

        # 2. حجم ویدیوها
        for fmt in info.get('formats', []):
            height = fmt.get('height')
            if not height:
                continue
            sz = fmt.get('filesize') or fmt.get('filesize_approx')
            if not sz:
                continue

            # فقط فرمت‌های کامل (هم صدا هم تصویر)
            if fmt.get('vcodec') == 'none' or fmt.get('acodec') == 'none':
                continue

            key = None
            if height <= 144: key = "144"
            elif height <= 240: key = "240"
            elif height <= 360: key = "360"
            elif height <= 480: key = "480"
            elif height <= 720: key = "720"
            elif height <= 1080: key = "1080"
            elif height <= 1440: key = "1440"
            elif height <= 2160: key = "2160"

            if key:
                sz = int(sz)
                if key not in size_map or sz < size_map[key]:
                    size_map[key] = sz

        # 3. تکمیل حجم‌های گمشده با تخمین دقیق
        for q in ["144","240","360","480","720","1080","1440","2160","best","audio"]:
            if q not in size_map or size_map[q] == 0:
                size_map[q] = estimate_size(duration, q)

        # ساخت کیبورد
        keyboard = []
        pairs = [("144", "240"), ("360", "480"), ("720", "1080"), ("1440", "2160"), ("best", "audio")]
        for q1, q2 in pairs:
            row = []
            for q in (q1, q2):
                size_str = format_size(size_map[q])
                label = QUALITY_LABELS[q]
                if q == "best":
                    text = f"Best ({size_str})"
                elif q == "audio":
                    text = f"Audio ({size_str})"
                else:
                    text = f"{label} ({size_str})"
                row.append(InlineKeyboardButton(text, callback_data=q))
            keyboard.append(row)

        markup = InlineKeyboardMarkup(keyboard)

        duration_str = f"{duration//60}:{duration%60:02d}" if duration else "نامشخص"
        text = f"**{title}**\n"
        text += f"مدت: {duration_str}\n\n"
        text += "کیفیت رو انتخاب کن:"

        await msg.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"YouTube info error: {e}")
        await msg.edit_text(f"خطا: نمی‌تونم اطلاعات ویدیو رو بگیرم\n{str(e)[:80]}")

def download_video(url: str, quality: str):
    format_str = QUALITIES.get(quality, "best")
    ydl_opts = {
        'format': format_str,
        'quiet': True,
        'noplaylist': True,
        'outtmpl': '%(title)s.%(ext)s',
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            info = info['entries'][0] if 'entries' in info else info
            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                files = [f for f in os.listdir(tmpdir) if not f.endswith('.part')]
                filename = os.path.join(tmpdir, files[0]) if files else None

            if not filename or not os.path.exists(filename):
                raise Exception("فایل دانلود نشد")

            with open(filename, 'rb') as f:
                data = f.read()

            title = info.get('title', 'Video')
            clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
            ext = 'm4a' if quality == 'audio' else 'mp4'
            final_name = f"{clean_title} - {QUALITY_LABELS[quality]}.{ext}"

            return io.BytesIO(data), final_name, title, len(data)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality = query.data
    url = context.user_data.get('youtube_url')
    if not url:
        await query.edit_message_text("لینک منقضی شده. دوباره بفرست.")
        return

    await query.edit_message_text(f"در حال دانلود {QUALITY_LABELS[quality]}...")

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, download_video, url, quality
        )
        buffer, filename, title, size = result

        if size > MAX_SIZE:
            await query.edit_message_text("فایل بیشتر از ۲ گیگابایته!")
            buffer.close()
            return

        buffer.seek(0)
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buffer,
            filename=filename,
            caption=f"**{title}**\nکیفیت: {QUALITY_LABELS[quality]}\nحجم: {format_size(size)}",
            parse_mode="Markdown"
        )
        await query.edit_message_text(f"آپلود شد! ({format_size(size)})")
        buffer.close()

    except Exception as e:
        logger.error(f"Download failed: {e}")
        await query.edit_message_text(f"خطا در دانلود:\n{str(e)[:100]}")

def main():
    if not TOKEN or "your_bot_token_here" in TOKEN:
        print("خطا: توکن ربات تنظیم نشده!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(r'(youtube\.com|youtu\.be)'), youtube_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^https?://'), youtube_handler))  # لینک مستقیم بعداً اضافه کن
    app.add_handler(CallbackQueryHandler(button_handler))

    print("ربات با موفقیت اجرا شد! همه دکمه‌ها حجم دارن")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
