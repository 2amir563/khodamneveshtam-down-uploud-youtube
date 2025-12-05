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

**Features:**
• Shows file size for each quality option
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
            duration_sec_remain = duration_sec % 60
            
            # Get formats with sizes - بهبود یافته
            formats = info.get('formats', [])
            quality_sizes = {}
            
            # برای هر کیفیت، بهترین فرمت را پیدا کن
            quality_resolutions = {
                "144": 144,
                "240": 240,
                "360": 360,
                "480": 480,
                "720": 720,
                "1080": 1080,
                "1440": 1440,
                "2160": 2160,
                "best": 99999,  # عدد بزرگ برای بهترین کیفیت
            }
            
            # ابتدا فرمت‌های pre-merged (ویدیو + صدا) را بررسی کن
            for fmt in formats:
                height = fmt.get('height')
                filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                
                if not height or not filesize:
                    continue
                
                # بررسی کن که فرمت هم ویدیو و هم صدا داشته باشد
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    # برای هر کیفیت، مناسب‌ترین را پیدا کن
                    for quality_key, max_height in quality_resolutions.items():
                        if height <= max_height:
                            # اگر قبلی نداشتیم یا این یکی کوچکتر است
                            if quality_key not in quality_sizes or filesize < quality_sizes[quality_key]:
                                quality_sizes[quality_key] = filesize
                            break
            
            # برای کیفیت best، بزرگترین فایل را انتخاب کن
            best_formats = [fmt for fmt in formats 
                          if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none' 
                          and (fmt.get('filesize') or fmt.get('filesize_approx'))]
            
            if best_formats:
                # بزرگترین فایل را برای best انتخاب کن
                best_format = max(best_formats, key=lambda x: (x.get('filesize') or x.get('filesize_approx') or 0))
                quality_sizes["best"] = best_format.get('filesize') or best_format.get('filesize_approx')
            
            # برای audio formats
            audio_formats = [fmt for fmt in formats 
                           if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none'
                           and (fmt.get('filesize') or fmt.get('filesize_approx'))]
            
            if audio_formats:
                # بهترین کیفیت صدا (بالاترین بیت‌ریت)
                audio_format = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                quality_sizes["audio"] = audio_format.get('filesize') or audio_format.get('filesize_approx')
            
            # Create keyboard with sizes - بهبود یافته
            keyboard = []
            quality_order = ["144", "240", "360", "480", "720", "1080", "1440", "2160", "best", "audio"]
            
            for quality_key in quality_order:
                if quality_key in QUALITY_LABELS:
                    size_est = quality_sizes.get(quality_key)
                    
                    if size_est and size_est > 0:
                        size_str = format_file_size(size_est)
                        if quality_key == "best":
                            label = f"🎬 Best\n{size_str}"
                        elif quality_key == "audio":
                            label = f"🎵 Audio\n{size_str}"
                        else:
                            label = f"{QUALITY_LABELS[quality_key]}\n{size_str}"
                    else:
                        if quality_key == "best":
                            label = f"🎬 Best\nSize unknown"
                        elif quality_key == "audio":
                            label = f"🎵 Audio\nSize unknown"
                        else:
                            label = f"{QUALITY_LABELS[quality_key]}\nSize unknown"
                    
                    keyboard.append([InlineKeyboardButton(label, callback_data=quality_key)])
            
            custom_keyboard = InlineKeyboardMarkup(keyboard)
            
            # Show video info - بهبود یافته
            info_text = f"🎬 **{title[:100]}**\n"
            info_text += f"⏱️ Duration: {duration_min}:{duration_sec_remain:02d}\n"
            info_text += f"📊 Views: {info.get('view_count', 'N/A'):,}\n\n"
            info_text += "**Available qualities with estimated sizes:**\n"
            
            has_sizes = False
            for quality_key in quality_order:
                if quality_key in quality_sizes and quality_sizes[quality_key]:
                    has_sizes = True
                    size_est = quality_sizes[quality_key]
                    size_str = format_file_size(size_est)
                    
                    if quality_key == "best":
                        info_text += f"• 🎬 **Best**: ~{size_str}\n"
                    elif quality_key == "audio":
                        info_text += f"• 🎵 **Audio**: ~{size_str}\n"
                    else:
                        info_text += f"• **{QUALITY_LABELS[quality_key]}**: ~{size_str}\n"
            
            if not has_sizes:
                info_text += "⚠️ Size estimation not available for some qualities\n"
            
            info_text += f"\n📦 **Max size limit: 2GB**\n"
            info_text += "Select quality from buttons below:"
            
            await message.edit_text(
                info_text,
                parse_mode='Markdown',
                reply_markup=custom_keyboard
            )
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"YouTube download error: {e}")
        await message.edit_text(f"❌ YouTube Error: {str(e)[:200]}")
    except Exception as e:
        logger.error(f"YouTube info error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:200]}")

async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links"""
    url = update.message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        return
    
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("🔍 Checking link...")
    
    try:
        # Check file size first
        try:
            head_response = requests.head(url, allow_redirects=True, timeout=10)
            if head_response.status_code != 200:
                await message.edit_text("❌ Link not accessible")
                return
            
            # Try to get content-length
            content_length = head_response.headers.get('Content-Length')
            if content_length:
                file_size = int(content_length)
                if file_size > MAX_SIZE:
                    size_str = format_file_size(file_size)
                    await message.edit_text(f"❌ File too large ({size_str}), max 2GB")
                    return
                
                size_str = format_file_size(file_size)
                await message.edit_text(f"✅ Link accessible\n📦 File size: {size_str}\n⬇️ Downloading...")
            else:
                await message.edit_text("✅ Link accessible\n📦 Size: Unknown\n⬇️ Downloading...")
                
        except:
            await message.edit_text("⬇️ Downloading...")
        
        # Download file
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
        total_size = 0
        last_update = 0
        
        try:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    temp_file.write(chunk)
                    total_size += len(chunk)
                    
                    # Update progress every 5MB
                    if total_size - last_update > 5_000_000:
                        size_str = format_file_size(total_size)
                        await message.edit_text(f"⬇️ Downloading... ({size_str})")
                        last_update = total_size
                    
                    if total_size > MAX_SIZE:
                        size_str = format_file_size(total_size)
                        await message.edit_text(f"❌ File too large ({size_str}), max 2GB")
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
                           f"📦 **Size:** {size_str}\n"
                           f"🔗 [Link]({url})",
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
    except requests.exceptions.RequestException as e:
        logger.error(f"Direct link error: {e}")
        await message.edit_text(f"❌ Network Error: {str(e)[:100]}")
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
            'progress_hooks': [],
        }
        
        # Download to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=True)
                
                if 'entries' in result:
                    result = result['entries'][0]
                
                filename = ydl.prepare_filename(result)
                
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
                title = result.get('title', 'Unknown')
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                
                if quality == 'audio':
                    final_filename = f"{clean_title} - audio.m4a"
                else:
                    final_filename = f"{clean_title} - {quality}p.mp4"
                
                return buffer, final_filename, title, file_size
                
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None, None, None, None, f"Error: {str(e)[:100]}"

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
            await query.edit_message_text(f"❌ {result[4] if len(result) > 4 else 'Download failed'}")
            return
        
        buffer, filename, title, file_size = result
        
        if file_size > MAX_SIZE:
            size_str = format_file_size(file_size)
            await query.edit_message_text(f"❌ Video too large ({size_str}), max 2GB")
            buffer.close()
            return
        
        size_str = format_file_size(file_size)
        
        buffer.seek(0)
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=buffer,
                filename=filename,
                caption=f"✅ **{title[:100]}**\n"
                       f"🎯 **Quality:** {quality_label}\n"
                       f"📦 **Size:** {size_str}\n"
                       f"🔗 [YouTube Link]({url})",
                parse_mode='Markdown',
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300
            )
            await query.edit_message_text(f"✅ Upload complete! ({size_str})")
        except Exception as e:
            logger.error(f"Upload error: {e}")
            await query.edit_message_text(f"❌ Upload error: {str(e)[:100]}")
        finally:
            buffer.close()
            
    except Exception as e:
        logger.error(f"Button handler error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)[:100]}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 **Help Guide**

**Commands:**
/start - Start the bot
/help - Show this help message

**How to download from YouTube:**
1. Send a YouTube link
2. Bot will show available qualities with file sizes
3. Click on a quality button to download
4. Bot will upload the video to Telegram

**How to download direct links:**
1. Send any direct download link (http/https)
2. Bot will automatically download and send the file

**Notes:**
• Maximum file size: 2GB
• YouTube videos are downloaded without re-encoding (no ffmpeg required)
• Files are temporarily stored and deleted after upload
• If download fails, try a different quality

**Supported YouTube formats:**
• 144p to 2160p (4K)
• Audio only (m4a format)
• Best quality available
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
    app.add_handler(CommandHandler("help", help_command))
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
    print("Bot now shows file sizes for each quality option")
    print("=" * 50)
    
    # Add drop_pending_updates to avoid conflict
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
