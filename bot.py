#!/usr/bin/env python3
"""
YouTube & Direct-Link Telegram Bot
Memory-Only Stream  |  systemd service  |  Port none (polling)
Repo: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube 
"""
import os
import io
import logging
import tempfile
import mimetypes
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import yt_dlp
import aiohttp
from typing import Optional

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER = int(os.getenv("OWNER_ID", 0))
MAXSIZE = 2_000_000_000  # 2 GB
CHUNK = 512 * 1024  # 512 KB

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# ------------------ YouTube quality map ------------------
QUALITY_MAP = {
    "best": {"format": "bestvideo+bestaudio/best", "ext": "mp4"},
    "720": {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]", "ext": "mp4"},
    "480": {"format": "bestvideo[height<=480]+bestaudio/best[height<=480]", "ext": "mp4"},
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
    if update.message:
        await update.message.reply_text(
            "👋 سلام! من ربات دانلودکننده فایل و ویدیو هستم.\n\n"
            "🔗 **لینک‌های پشتیبانی شده:**\n"
            "• لینک یوتیوب (youtube.com, youtu.be)\n"
            "• لینک مستقیم دانلود (http/https)\n\n"
            "📝 **نحوه استفاده:**\n"
            "1. لینک یوتیوب بفرستید → کیفیت را انتخاب کنید\n"
            "2. لینک مستقیم بفرستید → دانلود خودکار\n\n"
            "⚠️ **محدودیت:** حجم فایل نباید بیشتر از ۲ گیگابایت باشد.",
            reply_markup=quality_keyboard()
        )

# ------------------ YouTube Handler ------------------
async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if "youtube.com" in text or "youtu.be" in text:
        context.user_data["link"] = text
        await update.message.reply_text(
            "🎯 کیفیت مورد نظر را انتخاب کنید:",
            reply_markup=quality_keyboard()
        )

# ------------------ YouTube Stream Download ------------------
async def download_youtube_stream(link: str, quality: str) -> Optional[tuple]:
    """Download YouTube video to memory buffer without saving to disk"""
    opts = QUALITY_MAP.get(quality, QUALITY_MAP["best"])
    
    ydl_opts = {
        "format": opts["format"],
        "outtmpl": "-",  # output to stdout
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extract_flat": False,
        "socket_timeout": 30,
        "no_color": True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First get info
            info = ydl.extract_info(link, download=False)
            title = info.get('title', 'Unknown')
            video_id = info.get('id', 'unknown')
            duration = info.get('duration', 0)
            
            # Check duration limit (optional)
            if duration > 7200:  # 2 hours
                return None, "ویدیو بیشتر از ۲ ساعت است!"
            
            # Create in-memory buffer
            buffer = io.BytesIO()
            
            # Download to buffer
            def progress_hook(d):
                pass  # You can add progress callback here
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                result = ydl_download.download([link])
                
                # Read from stdout if possible, or use alternative method
                temp_buffer = io.BytesIO()
                for chunk in ydl_download.stream_buffer:
                    temp_buffer.write(chunk)
                
                buffer = temp_buffer
                buffer.seek(0)
            
            filename = f"{video_id}.{opts['ext']}"
            return (buffer, filename, title)
            
    except yt_dlp.utils.DownloadError as e:
        log.error(f"YouTube download error: {e}")
        return None, "خطا در دانلود از یوتیوب!"
    except Exception as e:
        log.error(f"General error: {e}")
        return None, "خطای ناشناخته!"

# ------------------ Upload YouTube Video ------------------
async def upload_youtube_video(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               link: str, quality: str):
    chat_id = update.effective_chat.id
    query = update.callback_query
    
    if query:
        await query.edit_message_text("⬇️ در حال دانلود از یوتیوب...")
        message = query.message
    else:
        message = await context.bot.send_message(chat_id, "⬇️ در حال دانلود از یوتیوب...")
    
    try:
        result = await asyncio.to_thread(download_youtube_stream, link, quality)
        
        if isinstance(result, tuple) and len(result) == 3:
            buffer, filename, title = result
            
            if buffer.getbuffer().nbytes > MAXSIZE:
                await message.edit_text("❌ فایل بزرگ‌تر از ۲ گیگابایت است!")
                buffer.close()
                return
            
            # Send the file
            buffer.seek(0)
            await context.bot.send_document(
                chat_id=chat_id,
                document=buffer,
                filename=filename,
                caption=f"✅ **{title}**\n🎯 کیفیت: {quality}",
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300,
                pool_timeout=300
            )
            buffer.close()
            
            if query:
                await query.edit_message_text("✅ ویدیو با موفقیت آپلود شد!")
            else:
                await message.edit_text("✅ ویدیو با موفقیت آپلود شد!")
        else:
            error_msg = result[1] if result else "خطا در دانلود!"
            await message.edit_text(f"❌ {error_msg}")
            
    except Exception as e:
        log.error(f"Upload error: {e}")
        await message.edit_text(f"❌ خطا در آپلود: {str(e)}")

# ------------------ Direct Link Handler ------------------
async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        return
    
    message = await update.message.reply_text("🔍 در حال بررسی لینک...")
    
    try:
        # Check file size first
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as resp:
                if resp.status != 200:
                    await message.edit_text("❌ لینک معتبر نیست!")
                    return
                
                size = int(resp.headers.get('Content-Length', 0))
                if size > MAXSIZE:
                    await message.edit_text("❌ فایل بزرگ‌تر از ۲ گیگابایت است!")
                    return
        
        await message.edit_text("⬇️ در حال دانلود...")
        
        # Download in chunks and stream to Telegram
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    await message.edit_text("❌ خطا در دانلود فایل!")
                    return
                
                # Get filename from URL or headers
                content_disposition = resp.headers.get('Content-Disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"\'')
                else:
                    # Extract from URL
                    filename = url.split('/')[-1].split('?')[0] or "download"
                
                content_type = resp.headers.get('Content-Type', '')
                ext = mimetypes.guess_extension(content_type) or ''
                if not filename.endswith(ext) and ext:
                    filename += ext
                
                # Create a temporary file to stream
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                
                try:
                    # Download in chunks
                    total_size = 0
                    async for chunk in resp.content.iter_chunked(CHUNK):
                        if chunk:
                            temp_file.write(chunk)
                            total_size += len(chunk)
                            
                            if total_size > MAXSIZE:
                                await message.edit_text("❌ فایل بزرگ‌تر از ۲ گیگابایت است!")
                                temp_file.close()
                                os.unlink(temp_file.name)
                                return
                    
                    temp_file.close()
                    
                    # Upload to Telegram
                    with open(temp_file.name, 'rb') as file:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=file,
                            filename=filename,
                            caption=f"✅ دانلود شد\n🔗 {url[:50]}...",
                            read_timeout=300,
                            write_timeout=300,
                            connect_timeout=300
                        )
                    
                    await message.edit_text("✅ فایل با موفقیت آپلود شد!")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                        
    except asyncio.TimeoutError:
        await message.edit_text("❌ زمان اتصال به سرور به پایان رسید!")
    except Exception as e:
        log.error(f"Direct link error: {e}")
        await message.edit_text(f"❌ خطا در دانلود: {str(e)[:100]}")

# ------------------ Callback Handler ------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    link = context.user_data.get("link")
    
    if not link:
        await query.edit_message_text("❌ ابتدا لینک یوتیوب بفرستید.")
        return
    
    await upload_youtube_video(update, context, link, quality)

# ------------------ Error Handler ------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ خطای داخلی رخ داد!")

# ------------------ Main Function ------------------
def main():
    if not TOKEN:
        log.error("❌ BOT_TOKEN not found in .env file!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        youtube_handler
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^https?://') & ~filters.COMMAND,
        direct_link_handler
    ))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    log.info("🤖 ربات در حال راه‌اندازی...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
