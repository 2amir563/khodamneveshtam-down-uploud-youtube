#!/usr/bin/env python3
"""
Complete Telegram Download Bot - YouTube + Direct Links
With File Size Display for Each Quality
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
import subprocess
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# YouTube quality options - FORMATS THAT DON'T REQUIRE MERGING
# Using formats that already have both audio and video
QUALITIES = {
    "144": "best[height<=144][ext=mp4]/best[height<=144]",
    "240": "best[height<=240][ext=mp4]/best[height<=240]",
    "360": "best[height<=360][ext=mp4]/best[height<=360]",
    "480": "best[height<=480][ext=mp4]/best[height<=480]",
    "720": "best[height<=720][ext=mp4]/best[height<=720]",
    "1080": "best[height<=1080][ext=mp4]/best[height<=1080]",
    "1440": "best[height<=1440][ext=mp4]/best[height<=1440]",
    "2160": "best[height<=2160][ext=mp4]/best[height<=2160]",
    "best": "best[ext=mp4]/best",
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
    "best": "🎬 Best (MP4)",
    "audio": "🎵 Audio (M4A)"
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

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_quality_keyboard():
    """Create quality selection keyboard with all options"""
    has_ffmpeg = check_ffmpeg()
    
    keyboard = []
    
    # برای کیفیت‌های پایین که معمولا بدون ادغام هستند
    row1 = [
        InlineKeyboardButton(f"{QUALITY_LABELS['144']}", callback_data="144"),
        InlineKeyboardButton(f"{QUALITY_LABELS['240']}", callback_data="240"),
        InlineKeyboardButton(f"{QUALITY_LABELS['360']}", callback_data="360")
    ]
    keyboard.append(row1)
    
    row2 = [
        InlineKeyboardButton(f"{QUALITY_LABELS['480']}", callback_data="480"),
        InlineKeyboardButton(f"{QUALITY_LABELS['720']}", callback_data="720"),
        InlineKeyboardButton(f"{QUALITY_LABELS['1080']}", callback_data="1080")
    ]
    keyboard.append(row2)
    
    row3 = [
        InlineKeyboardButton(f"{QUALITY_LABELS['best']}", callback_data="best"),
        InlineKeyboardButton(f"{QUALITY_LABELS['audio']}", callback_data="audio")
    ]
    keyboard.append(row3)
    
    # اگر ffmpeg نباشد، دکمه‌های 1440p و 2160p را غیرفعال کنیم
    if has_ffmpeg:
        row4 = [
            InlineKeyboardButton(f"{QUALITY_LABELS['1440']}", callback_data="1440"),
            InlineKeyboardButton(f"{QUALITY_LABELS['2160']}", callback_data="2160")
        ]
        keyboard.append(row4)
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    has_ffmpeg = check_ffmpeg()
    
    welcome_text = """
🤖 **Welcome to Download Bot**

**I can download:**
• YouTube videos (choose from 10 quality options)
• Any direct download link (http/https)

**How to use:**
1. Send YouTube link → Choose quality (shows file size)
2. Send any direct link → Auto download

**Limits:**
• Max file size: 2GB
• No files stored on server
• Shows file size for each quality option
"""
    
    if not has_ffmpeg:
        welcome_text += "\n⚠️ **Warning:** ffmpeg not detected. Some features limited."
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_quality_keyboard()
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links - Get available formats with file sizes"""
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    message = await update.message.reply_text("🔍 Analyzing video formats...")
    has_ffmpeg = check_ffmpeg()
    
    try:
        # Get video info with all formats
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_color': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Store URL and info for later use
            context.user_data['youtube_url'] = url
            context.user_data['video_info'] = info
            
            title = info.get('title', 'Unknown')
            duration_sec = info.get('duration', 0)
            duration_min = duration_sec // 60
            
            # Get all formats with their file sizes
            formats = info.get('formats', [])
            
            # Group formats by resolution/quality
            quality_sizes = {}
            
            for fmt in formats:
                # Skip formats that require merging if ffmpeg not available
                if not has_ffmpeg and (fmt.get('vcodec') != 'none' and fmt.get('acodec') == 'none'):
                    continue  # Skip video-only formats
                
                height = fmt.get('height')
                format_note = fmt.get('format_note', '')
                filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                ext = fmt.get('ext', '')
                
                if not height and fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    # Audio format
                    quality_key = "audio"
                elif height:
                    # Map height to our quality keys
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
                else:
                    continue
                
                # Prefer MP4/M4A formats that don't require merging
                if ext in ['mp4', 'm4a']:
                    if quality_key not in quality_sizes or (filesize and filesize < quality_sizes[quality_key]):
                        if filesize:
                            quality_sizes[quality_key] = filesize
            
            # Create keyboard with size information
            keyboard = []
            
            # Define quality order
            quality_order = ["144", "240", "360", "480", "720", "1080", "audio", "best"]
            if has_ffmpeg:
                quality_order.extend(["1440", "2160"])
            
            row = []
            for quality_key in quality_order:
                if quality_key in QUALITY_LABELS:
                    # Get estimated size for this quality
                    size_est = quality_sizes.get(quality_key)
                    
                    if size_est:
                        size_str = format_file_size(size_est)
                        label = f"{QUALITY_LABELS[quality_key]} (~{size_str})"
                    else:
                        label = f"{QUALITY_LABELS[quality_key]} (Unknown size)"
                    
                    # Disable if no ffmpeg and high quality
                    if not has_ffmpeg and quality_key in ["1440", "2160"]:
                        continue
                    
                    row.append(InlineKeyboardButton(label, callback_data=quality_key))
                    
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
            
            if row:
                keyboard.append(row)
            
            custom_keyboard = InlineKeyboardMarkup(keyboard)
            
            # Show video info with estimated sizes
            info_text = f"🎬 **{title}**\n"
            info_text += f"⏱️ Duration: {duration_min} minutes\n"
            
            if not has_ffmpeg:
                info_text += "⚠️ *Limited: Using formats that don't require ffmpeg*\n"
            
            info_text += "\n📊 **Available qualities (estimated size):**\n"
            
            # Add size information for available qualities
            for quality_key in quality_order:
                if quality_key in quality_sizes:
                    size_est = quality_sizes[quality_key]
                    size_str = format_file_size(size_est)
                    
                    if quality_key == "best":
                        info_text += f"• 🎬 Best Quality (MP4): ~{size_str}\n"
                    elif quality_key == "audio":
                        info_text += f"• 🎵 Audio Only (M4A): ~{size_str}\n"
                    else:
                        info_text += f"• {QUALITY_LABELS[quality_key]}: ~{size_str}\n"
            
            info_text += "\nSelect quality:"
            
            await message.edit_text(
                info_text,
                parse_mode='Markdown',
                reply_markup=custom_keyboard
            )
            
    except Exception as e:
        logger.error(f"YouTube info error: {e}")
        await message.edit_text(f"❌ Error checking video: {str(e)[:100]}")

async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links (NOT YouTube)"""
    url = update.message.text.strip()
    
    # Skip if not a valid URL
    if not url.startswith(("http://", "https://")):
        return
    
    # Skip YouTube links
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("🔍 Checking link...")
    
    try:
        # First check if file exists and get size
        try:
            head_response = requests.head(url, allow_redirects=True, timeout=10)
            if head_response.status_code != 200:
                await message.edit_text("❌ Link not accessible")
                return
            
            # Check content length
            content_length = head_response.headers.get('Content-Length')
            if content_length:
                file_size = int(content_length)
                if file_size > MAX_SIZE:
                    await message.edit_text("❌ File too large (max 2GB)")
                    return
                elif file_size == 0:
                    await message.edit_text("❌ File is empty")
                    return
        except Exception as e:
            logger.warning(f"HEAD request failed: {e}")
            # Continue with GET request
        
        await message.edit_text("⬇️ Downloading...")
        
        # Download the file with progress tracking
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
        total_size = 0
        
        try:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    temp_file.write(chunk)
                    total_size += len(chunk)
                    
                    # Check size during download
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
                utf8_match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
                if utf8_match:
                    import urllib.parse
                    filename = urllib.parse.unquote(utf8_match.group(1))
                else:
                    regular_match = re.search(r'filename=["\']?([^"\']+)["\']?', content_disposition)
                    if regular_match:
                        filename = regular_match.group(1)
            
            if not filename:
                path_part = url.split('?')[0]
                filename = os.path.basename(path_part)
                
                if not filename or filename == '' or '.' not in filename:
                    filename = "download_file"
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Add proper extension if missing
            content_type = response.headers.get('Content-Type', '')
            if content_type:
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    if '.' not in filename:
                        filename = filename + ext
                    else:
                        existing_ext = os.path.splitext(filename)[1].lower()
                        if existing_ext != ext.lower():
                            name_part = os.path.splitext(filename)[0]
                            filename = name_part + ext
            
            # Format size for display
            size_str = format_file_size(total_size)
            
            # Send to Telegram
            with open(temp_file.name, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=filename,
                    caption=f"✅ **Download Complete**\n"
                           f"📁 File: `{filename}`\n"
                           f"📦 Size: {size_str}\n"
                           f"🔗 Source: {url[:50]}...",
                    parse_mode='Markdown',
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=300
                )
            
            await message.edit_text(f"✅ Upload complete! ({size_str})")
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except requests.exceptions.Timeout:
        await message.edit_text("❌ Connection timeout")
    except requests.exceptions.RequestException as e:
        await message.edit_text(f"❌ Download failed: {str(e)[:100]}")
    except Exception as e:
        logger.error(f"Direct link error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

def download_youtube_video(url: str, quality: str):
    """Download YouTube video with selected quality WITHOUT MERGING"""
    try:
        has_ffmpeg = check_ffmpeg()
        
        # Use formats that don't require merging
        format_str = QUALITIES.get(quality, "best[ext=mp4]/best")
        
        ydl_opts = {
            'format': format_str,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'no_color': True,
            # Critical: Disable post-processing if no ffmpeg
            'postprocessors': [],
        }
        
        # If ffmpeg is available, we can use more features
        if has_ffmpeg:
            ydl_opts.update({
                'merge_output_format': 'mp4',
            })
        else:
            # Without ffmpeg, only download single-file formats
            ydl_opts.update({
                'format': format_str,
                'postprocessors': [],
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Video')
            
            # Clean title for filename
            clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            clean_title = clean_title[:100]
            
            # Download to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = os.path.join(tmpdir, f'{clean_title}.%(ext)s')
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_downloader:
                    result = ydl_downloader.extract_info(url, download=True)
                    
                    if 'entries' in result:
                        result = result['entries'][0]
                    
                    # Get the downloaded filename
                    filename = ydl_downloader.prepare_filename(result)
                    
                    # Sometimes the file extension is wrong, find the actual file
                    if not os.path.exists(filename):
                        for file in os.listdir(tmpdir):
                            if not file.endswith('.part'):
                                filename = os.path.join(tmpdir, file)
                                break
                    
                    if not os.path.exists(filename):
                        return None, "File not found after download"
                    
                    # Read file into buffer
                    buffer = io.BytesIO()
                    with open(filename, 'rb') as f:
                        buffer.write(f.read())
                    
                    buffer.seek(0)
                    
                    # Get file info
                    file_size = buffer.getbuffer().nbytes
                    
                    # Create nice filename for Telegram
                    if quality == 'audio':
                        display_quality = "Audio"
                        final_ext = '.m4a'
                    else:
                        display_quality = f"{quality}p"
                        final_ext = '.mp4'
                    
                    final_filename = f"{clean_title[:50]} - {display_quality}{final_ext}"
                    
                    return buffer, final_filename, title, file_size
                    
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"YouTube download error: {e}")
        # Try alternative method
        return download_youtube_simple(url, quality)
    except Exception as e:
        logger.error(f"YouTube processing error: {e}")
        return None, f"Error: {str(e)[:100]}"

def download_youtube_simple(url: str, quality: str):
    """Alternative simple download method"""
    try:
        # Simple format selection
        if quality == 'audio':
            format_str = 'bestaudio[ext=m4a]/bestaudio'
        elif quality in ['144', '240', '360', '480']:
            format_str = f'best[height<={quality}][ext=mp4]/best[height<={quality}]'
        else:
            format_str = 'best[ext=mp4]/best'
        
        ydl_opts = {
            'format': format_str,
            'quiet': True,
            'noplaylist': True,
            'no_warnings': True,
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [],
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown Video')
                
                # Find downloaded file
                downloaded_files = []
                for file in os.listdir(tmpdir):
                    if not file.endswith('.part'):
                        downloaded_files.append(file)
                
                if not downloaded_files:
                    return None, "No file downloaded"
                
                filename = os.path.join(tmpdir, downloaded_files[0])
                
                # Read into buffer
                buffer = io.BytesIO()
                with open(filename, 'rb') as f:
                    buffer.write(f.read())
                
                buffer.seek(0)
                file_size = buffer.getbuffer().nbytes
                
                # Create filename
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                if quality == 'audio':
                    final_filename = f"{clean_title} - Audio.m4a"
                else:
                    final_filename = f"{clean_title} - {quality}p.mp4"
                
                return buffer, final_filename, title, file_size
                
    except Exception as e:
        logger.error(f"Simple download error: {e}")
        return None, f"Download failed: {str(e)[:100]}"

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ Send YouTube link first!")
        return
    
    # Get quality label
    quality_label = QUALITY_LABELS.get(quality, quality)
    
    await query.edit_message_text(f"⬇️ Downloading {quality_label}...")
    
    try:
        # Check ffmpeg availability
        has_ffmpeg = check_ffmpeg()
        
        if not has_ffmpeg and quality in ["1440", "2160"]:
            await query.edit_message_text("❌ This quality requires ffmpeg. Install ffmpeg first.")
            return
        
        # Download in background thread
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_youtube_video, url, quality)
        
        if result[0] is None:
            error_msg = result[1]
            await query.edit_message_text(f"❌ {error_msg}")
            return
        
        buffer, filename, title, file_size = result
        
        # Check size
        if file_size > MAX_SIZE:
            await query.edit_message_text("❌ Video too large (max 2GB)")
            buffer.close()
            return
        
        # Format size for display
        size_str = format_file_size(file_size)
        
        # Send to Telegram
        buffer.seek(0)
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=buffer,
                filename=filename,
                caption=f"✅ **{title}**\n"
                       f"🎯 Quality: {quality_label}\n"
                       f"📦 Size: {size_str}\n"
                       f"📥 Source: YouTube",
                parse_mode='Markdown',
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300
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
    """Main function to start the bot"""
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN not found in .env file!")
        print("Please add your bot token to the .env file:")
        print("BOT_TOKEN=your_token_here")
        print("\nEdit the file: nano ~/telegram-download-bot/.env")
        return
    
    # Check system requirements
    print("=" * 50)
    print("🤖 Telegram Download Bot Starting...")
    print("=" * 50)
    
    # Check ffmpeg
    if check_ffmpeg():
        print("✅ ffmpeg detected: Video merging available")
    else:
        print("⚠️  ffmpeg not found: Using single-file formats only")
        print("   Install ffmpeg for better quality: sudo apt install ffmpeg")
    
    print(f"📁 Max file size: {format_file_size(MAX_SIZE)}")
    print("🎯 YouTube qualities: Shows estimated file sizes")
    print("🔗 Direct links: Supported")
    print("=" * 50)
    print("Press Ctrl+C to stop the bot")
    
    # Create bot application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    
    # YouTube links handler
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        youtube_handler
    ))
    
    # Direct links handler (NOT YouTube)
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^https?://') & 
        ~filters.Regex(r'youtube\.com|youtu\.be') & 
        ~filters.COMMAND,
        direct_link_handler
    ))
    
    # Button (quality selection) handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Add error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text("❌ An error occurred. Please try again.")
            except:
                pass
    
    app.add_error_handler(error_handler)
    
    # Start the bot
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
