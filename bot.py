#!/usr/bin/env python3
"""
Telegram Download Bot - YouTube + Direct Links
FFmpeg Fixed Version
GitHub: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube
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

# YouTube quality options - FIXED: Use pre-merged formats only
QUALITIES = {
    "144": "best[height<=144]/best",
    "240": "best[height<=240]/best",
    "360": "best[height<=360]/best",
    "480": "best[height<=480]/best",
    "720": "best[height<=720]/best",
    "1080": "best[height<=1080]/best",
    "1440": "best[height<=1440]/best",
    "2160": "best[height<=2160]/best",
    "best": "best",
    "audio": "bestaudio[ext=m4a]/bestaudio"
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
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(bytes_size, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_size / p, 2)
    
    return f"{s} {size_names[i]}"

def get_quality_keyboard():
    """Create quality selection keyboard"""
    keyboard = [
        [InlineKeyboardButton(f"{QUALITY_LABELS['144']}", callback_data="144"),
         InlineKeyboardButton(f"{QUALITY_LABELS['240']}", callback_data="240")],
        [InlineKeyboardButton(f"{QUALITY_LABELS['360']}", callback_data="360"),
         InlineKeyboardButton(f"{QUALITY_LABELS['480']}", callback_data="480")],
        [InlineKeyboardButton(f"{QUALITY_LABELS['720']}", callback_data="720"),
         InlineKeyboardButton(f"{QUALITY_LABELS['1080']}", callback_data="1080")],
        [InlineKeyboardButton(f"{QUALITY_LABELS['1440']}", callback_data="1440"),
         InlineKeyboardButton(f"{QUALITY_LABELS['2160']}", callback_data="2160")],
        [InlineKeyboardButton(f"{QUALITY_LABELS['best']}", callback_data="best"),
         InlineKeyboardButton(f"{QUALITY_LABELS['audio']}", callback_data="audio")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🤖 **Welcome to Download Bot**

**I can download:**
• YouTube videos (choose from 10 quality options)
• Any direct download link (http/https)

**How to use:**
1. Send YouTube link → Choose quality
2. Send any direct link → Auto download

**Limits:**
• Max file size: 2GB
• No files stored on server

Send me a link to start!
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_quality_keyboard()
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links"""
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    message = await update.message.reply_text("🔍 Checking video...")
    
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
            context.user_data['video_info'] = info
            
            title = info.get('title', 'Unknown')
            duration_sec = info.get('duration', 0)
            duration_min = duration_sec // 60
            
            # Get formats with sizes
            formats = info.get('formats', [])
            quality_sizes = {}
            
            # Find pre-merged formats (with both video and audio)
            for fmt in formats:
                height = fmt.get('height')
                filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                
                if not height or not filesize:
                    continue
                
                # Only consider formats that already have audio (vcodec and acodec both not 'none')
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    # Map to our quality keys
                    if height <= 144:
                        quality_key = "144"
                    elif height <= 240:
                        quality_key = "240"
                    elif height <= 360:
                        quality_key = "360"
                    elif height <= 480:
                        quality_key = "480"
                    elif height <= 720:
                        quality_key = "720"
                    elif height <= 1080:
                        quality_key = "1080"
                    elif height <= 1440:
                        quality_key = "1440"
                    elif height <= 2160:
                        quality_key = "2160"
                    else:
                        quality_key = "best"
                    
                    # Store size
                    if quality_key not in quality_sizes:
                        quality_sizes[quality_key] = filesize
                    elif filesize < quality_sizes[quality_key]:
                        quality_sizes[quality_key] = filesize
            
            # For audio formats
            for fmt in formats:
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                    if filesize:
                        quality_sizes["audio"] = filesize
                        break
            
            # Create keyboard with sizes - این بخش اصلاح شده
            keyboard = []
            quality_order = ["144", "240", "360", "480", "720", "1080", "1440", "2160", "best", "audio"]
            
            row = []
            for quality_key in quality_order:
                if quality_key in QUALITY_LABELS:
                    size_est = quality_sizes.get(quality_key)
                    
                    if size_est:
                        size_str = format_file_size(size_est)
                        # اصلاح برچسب دکمه‌ها برای نمایش حجم
                        if quality_key == "best":
                            label = f"🎬 Best\n({size_str})"
                        elif quality_key == "audio":
                            label = f"🎵 Audio\n({size_str})"
                        else:
                            label = f"{QUALITY_LABELS[quality_key]}\n({size_str})"
                    else:
                        # اگر حجم تخمینی موجود نبود
                        if quality_key == "best":
                            label = f"🎬 Best\n(اندازه نامعلوم)"
                        elif quality_key == "audio":
                            label = f"🎵 Audio\n(اندازه نامعلوم)"
                        else:
                            label = f"{QUALITY_LABELS[quality_key]}\n(اندازه نامعلوم)"
                    
                    row.append(InlineKeyboardButton(label, callback_data=quality_key))
                    
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
            
            if row:
                keyboard.append(row)
            
            custom_keyboard = InlineKeyboardMarkup(keyboard)
            
            # Show video info
            info_text = f"🎬 **{title}**\n"
            info_text += f"⏱️ Duration: {duration_min} minutes\n\n"
            info_text += "📊 Available qualities:\n"
            
            for quality_key in quality_order:
                if quality_key in quality_sizes:
                    size_est = quality_sizes[quality_key]
                    size_str = format_file_size(size_est)
                    
                    if quality_key == "best":
                        info_text += f"• 🎬 Best: ~{size_str}\n"
                    elif quality_key == "audio":
                        info_text += f"• 🎵 Audio: ~{size_str}\n"
                    else:
                        info_text += f"• {QUALITY_LABELS[quality_key]}: ~{size_str}\n"
            
            info_text += "\nSelect quality (size estimated):"
            
            await message.edit_text(
                info_text,
                parse_mode='Markdown',
                reply_markup=custom_keyboard
            )
            
    except Exception as e:
        logger.error(f"YouTube info error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links"""
    url = update.message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        return
    
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("🔍 Checking link...")
    
    try:
        # Check file
        try:
            head_response = requests.head(url, allow_redirects=True, timeout=10)
            if head_response.status_code != 200:
                await message.edit_text("❌ Link not accessible")
                return
        except:
            pass
        
        await message.edit_text("⬇️ Downloading...")
        
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
                        await message.edit_text("❌ File too large (max 2GB)")
                        temp_file.close()
                        os.unlink(temp_file.name)
                        return
            
            temp_file.close()
            
            # Get filename
            filename = None
            content_disposition = response.headers.get('Content-Disposition', '')
            
            if content_disposition:
                match = re.search(r'filename=["\']?([^"\']+)["\']?', content_disposition)
                if match:
                    filename = match.group(1)
            
            if not filename:
                filename = url.split('/')[-1].split('?')[0] or "download"
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Add extension
            content_type = response.headers.get('Content-Type', '')
            if content_type:
                ext = mimetypes.guess_extension(content_type)
                if ext and not filename.endswith(ext):
                    filename += ext
            
            size_str = format_file_size(total_size)
            
            # Send to Telegram
            with open(temp_file.name, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=filename,
                    caption=f"✅ **Download Complete**\n"
                           f"📦 Size: {size_str}\n"
                           f"🔗 {url[:50]}...",
                    parse_mode='Markdown',
                    read_timeout=300,
                    write_timeout=300
                )
            
            await message.edit_text(f"✅ Upload complete! ({size_str})")
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except requests.exceptions.Timeout:
        await message.edit_text("❌ Connection timeout")
    except Exception as e:
        logger.error(f"Direct link error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

def download_youtube_video(url: str, quality: str):
    """Download YouTube video - FIXED: Only use pre-merged formats"""
    try:
        format_str = QUALITIES.get(quality, "best")
        
        ydl_opts = {
            'format': format_str,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'no_color': True,
        }
        
        # IMPORTANT: Don't use merge_output_format to avoid ffmpeg requirement
        # Use formats that already have both video and audio
        
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
                            return None, "File not downloaded"
                    
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
        return None, f"Error: {str(e)[:100]}"

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ Send YouTube link first!")
        return
    
    quality_label = QUALITY_LABELS.get(quality, quality)
    await query.edit_message_text(f"⬇️ Downloading {quality_label}...")
    
    try:
        # Download in background
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_youtube_video, url, quality)
        
        if result[0] is None:
            await query.edit_message_text(f"❌ {result[1]}")
            return
        
        buffer, filename, title, file_size = result
        
        if file_size > MAX_SIZE:
            await query.edit_message_text("❌ Video too large (max 2GB)")
            buffer.close()
            return
        
        size_str = format_file_size(file_size)
        
        buffer.seek(0)
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=buffer,
                filename=filename,
                caption=f"✅ **{title}**\n"
                       f"🎯 Quality: {quality_label}\n"
                       f"📦 Size: {size_str}",
                parse_mode='Markdown',
                read_timeout=300,
                write_timeout=300
            )
            await query.edit_message_text(f"✅ Upload complete! ({size_str})")
        except Exception as e:
            await query.edit_message_text(f"❌ Upload error: {str(e)[:100]}")
        finally:
            buffer.close()
            
    except Exception as e:
        logger.error(f"Button handler error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)[:100]}")

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
    
    # Error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        # Don't show error message to user for conflict errors
        if "Conflict" not in str(context.error):
            if update and update.effective_message:
                try:
                    await update.effective_message.reply_text("❌ An error occurred. Please try again.")
                except:
                    pass
    
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("🤖 Bot starting...")
    print("=" * 50)
    print("Telegram Download Bot Started!")
    print("=" * 50)
    
    # Add drop_pending_updates to avoid conflict
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
