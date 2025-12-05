#!/usr/bin/env python3
"""
Simple Telegram Download Bot - YouTube + Direct Links
NO FFMPEG REQUIRED - Uses MP4 formats only
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

# YouTube quality options - ONLY SINGLE FILE FORMATS (no merging)
QUALITIES = {
    "144": "best[height<=144][ext=mp4]/best[height<=144]/worst[height<=144]",
    "240": "best[height<=240][ext=mp4]/best[height<=240]/worst[height<=240]",
    "360": "best[height<=360][ext=mp4]/best[height<=360]/worst[height<=360]",
    "480": "best[height<=480][ext=mp4]/best[height<=480]/worst[height<=480]",
    "720": "best[height<=720][ext=mp4]/best[height<=720]/worst[height<=720]",
    "1080": "best[height<=1080][ext=mp4]/best[height<=1080]/worst[height<=1080]",
    "audio": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio"
}

QUALITY_LABELS = {
    "144": "144p (MP4)",
    "240": "240p (MP4)",
    "360": "360p (MP4)",
    "480": "480p (MP4)",
    "720": "720p (MP4)",
    "1080": "1080p (MP4)",
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🤖 **Welcome to Simple Download Bot**

**I can download:**
• YouTube videos (7 quality options)
• Any direct download link (http/https)

**Features:**
• No ffmpeg required
• Shows file size before download
• Max file size: 2GB
• Files are not stored on server

**How to use:**
1. Send YouTube link → Choose quality
2. Send any direct link → Auto download

Send me a link to start!
"""
    
    keyboard = [
        [InlineKeyboardButton("144p", callback_data="144"),
         InlineKeyboardButton("240p", callback_data="240")],
        [InlineKeyboardButton("360p", callback_data="360"),
         InlineKeyboardButton("480p", callback_data="480")],
        [InlineKeyboardButton("720p", callback_data="720"),
         InlineKeyboardButton("1080p", callback_data="1080")],
        [InlineKeyboardButton("🎵 Audio", callback_data="audio")]
    ]
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links - Get available formats"""
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    message = await update.message.reply_text("🔍 Checking video...")
    
    try:
        # Get video info - ONLY SINGLE FILE FORMATS
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_color': True,
            'format': 'best[ext=mp4]/best'  # Only MP4 formats
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Store URL for later use
            context.user_data['youtube_url'] = url
            context.user_data['video_info'] = info
            
            title = info.get('title', 'Unknown')
            duration_sec = info.get('duration', 0)
            duration_min = duration_sec // 60
            
            # Get available formats
            formats = info.get('formats', [])
            
            # Find sizes for each quality
            quality_sizes = {}
            
            for fmt in formats:
                # Skip formats that are not complete (video+audio in one file)
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    height = fmt.get('height')
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                    ext = fmt.get('ext', '')
                    
                    # Only use MP4 or M4A files
                    if ext not in ['mp4', 'm4a', 'webm']:
                        continue
                    
                    if height:
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
                        else:
                            continue
                    elif fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        quality_key = "audio"
                    else:
                        continue
                    
                    # Store size
                    if filesize:
                        quality_sizes[quality_key] = filesize
            
            # Create keyboard with available qualities
            keyboard = []
            available_qualities = []
            
            # Check which qualities are available
            for quality in ["144", "240", "360", "480", "720", "1080", "audio"]:
                if quality in quality_sizes:
                    available_qualities.append(quality)
            
            # Create keyboard rows
            row = []
            for quality in available_qualities:
                if quality == "audio":
                    label = "🎵 Audio"
                else:
                    label = f"{quality}p"
                
                row.append(InlineKeyboardButton(label, callback_data=quality))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            
            if row:
                keyboard.append(row)
            
            if not keyboard:
                await message.edit_text("❌ No downloadable formats found for this video")
                return
            
            # Create info text
            info_text = f"🎬 **{title}**\n"
            info_text += f"⏱️ Duration: {duration_min} minutes\n\n"
            info_text += "📊 **Available qualities:**\n"
            
            for quality in available_qualities:
                size = quality_sizes.get(quality)
                if size:
                    size_str = format_file_size(size)
                    if quality == "audio":
                        info_text += f"• 🎵 Audio: {size_str}\n"
                    else:
                        info_text += f"• {quality}p: {size_str}\n"
                else:
                    if quality == "audio":
                        info_text += f"• 🎵 Audio (size unknown)\n"
                    else:
                        info_text += f"• {quality}p (size unknown)\n"
            
            info_text += "\nSelect quality:"
            
            await message.edit_text(
                info_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"YouTube info error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links"""
    url = update.message.text.strip()
    
    if not url.startswith(("http://", "https://")) or "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("🔍 Checking link...")
    
    try:
        # Check if file exists
        head_response = requests.head(url, allow_redirects=True, timeout=10)
        if head_response.status_code != 200:
            await message.edit_text("❌ Link not accessible")
            return
        
        content_length = head_response.headers.get('Content-Length')
        if content_length:
            file_size = int(content_length)
            if file_size > MAX_SIZE:
                await message.edit_text("❌ File too large (max 2GB)")
                return
        
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
                path_part = url.split('?')[0]
                filename = os.path.basename(path_part)
                if not filename or '.' not in filename:
                    filename = "download_file"
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Add extension if missing
            content_type = response.headers.get('Content-Type', '')
            if content_type:
                ext = mimetypes.guess_extension(content_type)
                if ext and '.' not in filename:
                    filename = filename + ext
            
            # Format size
            size_str = format_file_size(total_size)
            
            # Send to Telegram
            with open(temp_file.name, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=filename,
                    caption=f"✅ **Download Complete**\n"
                           f"📁 File: `{filename}`\n"
                           f"📦 Size: {size_str}",
                    parse_mode='Markdown'
                )
            
            await message.edit_text(f"✅ Upload complete! ({size_str})")
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.error(f"Direct link error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

def download_youtube_simple(url: str, quality: str):
    """Simple YouTube download - NO MERGING REQUIRED"""
    try:
        # Format selection - ONLY single file formats
        if quality == "audio":
            format_str = "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio"
        else:
            height = quality
            format_str = f"best[height<={height}][ext=mp4]/best[height<={height}]/worst[height<={height}]"
        
        ydl_opts = {
            'format': format_str,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'no_color': True,
            # CRITICAL: Disable all post-processing
            'postprocessors': [],
            'merge_output_format': None,
            'outtmpl': '%(title)s.%(ext)s',
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Video')
                
                # Clean title for filename
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                
                # Find the downloaded file
                downloaded_file = None
                for file in os.listdir(tmpdir):
                    if not file.endswith('.part'):
                        downloaded_file = os.path.join(tmpdir, file)
                        break
                
                if not downloaded_file:
                    return None, "No file downloaded"
                
                # Read file into buffer
                with open(downloaded_file, 'rb') as f:
                    file_content = f.read()
                
                buffer = io.BytesIO(file_content)
                file_size = len(file_content)
                
                # Create final filename
                ext = os.path.splitext(downloaded_file)[1]
                if quality == "audio":
                    final_filename = f"{clean_title} - Audio.m4a"
                else:
                    final_filename = f"{clean_title} - {quality}p.mp4"
                
                return buffer, final_filename, title, file_size
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None, f"Download failed: {str(e)}"

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ Please send a YouTube link first")
        return
    
    await query.edit_message_text(f"⬇️ Downloading {quality}p...")
    
    try:
        # Download video
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_youtube_simple, url, quality)
        
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
        
        size_str = format_file_size(file_size)
        
        # Send to Telegram
        buffer.seek(0)
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=buffer,
                filename=filename,
                caption=f"✅ **{title}**\n"
                       f"📦 Size: {size_str}\n"
                       f"🎯 Quality: {quality}p",
                parse_mode='Markdown'
            )
            await query.edit_message_text(f"✅ Upload complete! ({size_str})")
        except Exception as e:
            await query.edit_message_text(f"❌ Upload error: {str(e)[:100]}")
        finally:
            buffer.close()
            
    except Exception as e:
        logger.error(f"Button error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)[:100]}")

def main():
    """Main function"""
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN not found!")
        print("Edit .env file and add your bot token")
        return
    
    print("=" * 50)
    print("🤖 Simple Telegram Download Bot")
    print("✅ No ffmpeg required")
    print("📁 Max file size: 2GB")
    print("=" * 50)
    
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
        logger.error(f"Error: {context.error}")
    
    app.add_error_handler(error_handler)
    
    # Start bot
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
