#!/usr/bin/env python3
"""
Telegram Download Bot - YouTube + Direct Links
راه‌حل مطمئن برای نمایش حجم همه کیفیت‌ها
"""

import os
import io
import logging
import tempfile
import mimetypes
import asyncio
import re
import math
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import yt_dlp
import aiohttp
import requests

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID", "0")
MAX_SIZE = 2_000_000_000  # 2GB
CHUNK_SIZE = 512 * 1024   # 512KB

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# YouTube quality options
QUALITIES = {
    "144": "best[height<=144]",
    "240": "best[height<=240]",
    "360": "best[height<=360]",
    "480": "best[height<=480]",
    "720": "best[height<=720]",
    "1080": "best[height<=1080]",
    "1440": "best[height<=1440]",
    "2160": "best[height<=2160]",
    "best": "best",
    "audio": "bestaudio[ext=m4a]"
}

QUALITY_LABELS = {
    "144": "144p",
    "240": "240p",
    "360": "360p",
    "480": "480p",
    "720": "720p",
    "1080": "1080p",
    "1440": "1440p",
    "2160": "2160p",
    "best": "🎬 Best",
    "audio": "🎵 Audio"
}

def format_file_size(bytes_size):
    """Format file size to human readable format"""
    if bytes_size == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(bytes_size, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_size / p, 2)
    
    return f"{s}{size_names[i]}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🤖 **Welcome to Download Bot**

**I can download:**
• YouTube videos (choose quality + see size)
• Any direct download link

**How to use:**
1. Send YouTube link → Choose quality
2. Send any direct link → Auto download

**Limits:**
• Max file size: 2GB
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links - راه‌حل مطمئن برای نمایش حجم"""
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    message = await update.message.reply_text("🔍 در حال دریافت اطلاعات...")
    
    try:
        # Get video info
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            context.user_data['youtube_url'] = url
            
            title = info.get('title', 'Unknown')
            duration_sec = info.get('duration', 0)
            duration_min = duration_sec // 60
            
            # Get video filesize for estimation
            video_size = info.get('filesize') or info.get('filesize_approx')
            if not video_size:
                # Try to estimate from formats
                formats = info.get('formats', [])
                for fmt in formats:
                    if fmt.get('filesize'):
                        video_size = fmt.get('filesize')
                        break
                    elif fmt.get('filesize_approx'):
                        video_size = fmt.get('filesize_approx')
                        break
            
            # اگر حجم اصلی پیدا نشد، تخمین بزن بر اساس مدت
            if not video_size and duration_sec > 0:
                # تخمین: 1 دقیقه ≈ 10MB برای کیفیت متوسط
                video_size = int(duration_sec / 60 * 10 * 1024 * 1024)
            
            # محاسبه حجم برای همه کیفیت‌ها
            quality_sizes = {}
            
            if video_size:
                base_size = video_size
                # نسبت‌های تخمین بر اساس کیفیت
                size_ratios = {
                    "144": 0.15,   # 15% از حجم اصلی
                    "240": 0.25,   # 25% از حجم اصلی
                    "360": 0.40,   # 40% از حجم اصلی
                    "480": 0.60,   # 60% از حجم اصلی
                    "720": 0.85,   # 85% از حجم اصلی
                    "1080": 1.0,   # 100% از حجم اصلی
                    "1440": 1.5,   # 150% از حجم اصلی
                    "2160": 2.5,   # 250% از حجم اصلی
                    "best": 1.2,   # 120% از حجم اصلی
                    "audio": 0.08  # 8% از حجم اصلی (فقط صدا)
                }
                
                for quality, ratio in size_ratios.items():
                    quality_sizes[quality] = int(base_size * ratio)
            
            # اگر تخمین هم کار نکرد، مقادیر پیش‌فرض
            if not quality_sizes:
                default_sizes = {
                    "144": 2 * 1024 * 1024,      # 2MB
                    "240": 5 * 1024 * 1024,      # 5MB
                    "360": 10 * 1024 * 1024,     # 10MB
                    "480": 20 * 1024 * 1024,     # 20MB
                    "720": 40 * 1024 * 1024,     # 40MB
                    "1080": 80 * 1024 * 1024,    # 80MB
                    "1440": 120 * 1024 * 1024,   # 120MB
                    "2160": 200 * 1024 * 1024,   # 200MB
                    "best": 100 * 1024 * 1024,   # 100MB
                    "audio": 3 * 1024 * 1024     # 3MB
                }
                
                # تطبیق با مدت ویدیو
                if duration_sec > 0:
                    duration_factor = duration_sec / 60  # فاکتور بر اساس دقیقه
                    for quality in default_sizes:
                        default_sizes[quality] = int(default_sizes[quality] * duration_factor)
                
                quality_sizes = default_sizes
            
            # ایجاد کیبورد با حجم - همیشه حجم نمایش داده می‌شود
            keyboard = []
            quality_order = ["144", "240", "360", "480", "720", "1080", "1440", "2160", "best", "audio"]
            
            # گروه‌بندی دکمه‌ها
            groups = [
                ["144", "240"],
                ["360", "480"],
                ["720", "1080"],
                ["1440", "2160"],
                ["best", "audio"]
            ]
            
            for group in groups:
                row = []
                for quality_key in group:
                    if quality_key in QUALITY_LABELS:
                        size_est = quality_sizes.get(quality_key, 0)
                        size_str = format_file_size(size_est)
                        
                        # نمایش حجم در یک خط کنار کیفیت
                        if quality_key == "best":
                            label = f"🎬 Best ({size_str})"
                        elif quality_key == "audio":
                            label = f"🎵 Audio ({size_str})"
                        else:
                            label = f"{QUALITY_LABELS[quality_key]} ({size_str})"
                        
                        row.append(InlineKeyboardButton(label, callback_data=quality_key))
                
                if row:
                    keyboard.append(row)
            
            custom_keyboard = InlineKeyboardMarkup(keyboard)
            
            # نمایش اطلاعات ویدیو
            info_text = f"🎬 **{title}**\n"
            info_text += f"⏱️ مدت: {duration_min} دقیقه\n\n"
            info_text += "📊 انتخاب کیفیت (حجم تخمینی):"
            
            await message.edit_text(
                info_text,
                parse_mode='Markdown',
                reply_markup=custom_keyboard
            )
            
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        await message.edit_text(f"❌ خطا: {str(e)[:100]}")

async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links"""
    url = update.message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        return
    
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("🔍 بررسی لینک...")
    
    try:
        await message.edit_text("⬇️ در حال دانلود...")
        
        # Download file
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
        total_size = 0
        
        try:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    temp_file.write(chunk)
                    total_size += len(chunk)
                    
                    if total_size > MAX_SIZE:
                        await message.edit_text("❌ فایل خیلی بزرگ است (حداکثر 2GB)")
                        temp_file.close()
                        os.unlink(temp_file.name)
                        return
            
            temp_file.close()
            
            # Get filename
            filename = url.split('/')[-1].split('?')[0] or "download"
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            size_str = format_file_size(total_size)
            
            # Send to Telegram
            with open(temp_file.name, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=filename,
                    caption=f"✅ **دانلود کامل**\n📦 حجم: {size_str}",
                    parse_mode='Markdown'
                )
            
            await message.edit_text(f"✅ آپلود کامل! ({size_str})")
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.error(f"Direct link error: {e}")
        await message.edit_text(f"❌ خطا: {str(e)[:100]}")

def download_youtube_video(url: str, quality: str):
    """Download YouTube video"""
    try:
        format_str = QUALITIES.get(quality, "best")
        
        ydl_opts = {
            'format': format_str,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            
            # Download to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    result = ydl2.extract_info(url, download=True)
                    
                    if 'entries' in result:
                        result = result['entries'][0]
                    
                    filename = ydl2.prepare_filename(result)
                    
                    # Find the actual file
                    if not os.path.exists(filename):
                        files = [f for f in os.listdir(tmpdir) 
                                if not f.endswith('.part')]
                        if files:
                            filename = os.path.join(tmpdir, files[0])
                        else:
                            return None, "فایل دانلود نشد"
                    
                    # Read to buffer
                    buffer = io.BytesIO()
                    with open(filename, 'rb') as f:
                        buffer.write(f.read())
                    
                    buffer.seek(0)
                    file_size = buffer.getbuffer().nbytes
                    
                    # Create filename
                    clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                    if quality == 'audio':
                        final_filename = f"{clean_title} - audio.m4a"
                    else:
                        final_filename = f"{clean_title} - {quality}p.mp4"
                    
                    return buffer, final_filename, title, file_size
                    
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None, f"خطا: {str(e)[:100]}"

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ ابتدا لینک یوتیوب ارسال کنید!")
        return
    
    quality_label = QUALITY_LABELS.get(quality, quality)
    await query.edit_message_text(f"⬇️ دانلود {quality_label}...")
    
    try:
        # Download in background
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_youtube_video, url, quality)
        
        if result[0] is None:
            await query.edit_message_text(f"❌ {result[1]}")
            return
        
        buffer, filename, title, file_size = result
        
        if file_size > MAX_SIZE:
            await query.edit_message_text("❌ ویدیو خیلی بزرگ است (حداکثر 2GB)")
            buffer.close()
            return
        
        size_str = format_file_size(file_size)
        
        buffer.seek(0)
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=buffer,
                filename=filename,
                caption=f"✅ **{title}**\n🎯 کیفیت: {quality_label}\n📦 حجم واقعی: {size_str}",
                parse_mode='Markdown'
            )
            await query.edit_message_text(f"✅ آپلود کامل! ({size_str})")
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در آپلود: {str(e)[:100]}")
        finally:
            buffer.close()
            
    except Exception as e:
        logger.error(f"Button handler error: {e}")
        await query.edit_message_text(f"❌ خطا: {str(e)[:100]}")

def main():
    """Start the bot"""
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN not found in .env file!")
        print("Please edit .env file: nano ~/telegram-download-bot/.env")
        return
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        youtube_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^https?://') & 
        ~filters.Regex(r'youtube\.com|youtu\.be') & 
        ~filters.COMMAND,
        direct_link_handler
    ))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Start bot
    logger.info("🤖 Bot starting...")
    print("=" * 60)
    print("🤖 Telegram Download Bot Started!")
    print("📊 **با نمایش حجم برای همه کیفیت‌ها**")
    print("=" * 60)
    print("✨ Features:")
    print("  • نمایش حجم تخمینی برای همه 10 کیفیت")
    print("  • دانلود از یوتیوب و لینک مستقیم")
    print("  • حداکثر حجم 2GB")
    print("=" * 60)
    print("⚠️  توجه: اعداد نمایش داده شده تخمینی هستند")
    print("حجم واقعی ممکن است متفاوت باشد")
    print("=" * 60)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
