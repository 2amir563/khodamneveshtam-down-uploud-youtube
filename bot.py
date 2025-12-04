#!/usr/bin/env python3
"""
Complete Telegram Download Bot - YouTube + Direct Links
With All YouTube Quality Options
GitHub: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube
"""

import os
import io
import logging
import tempfile
import mimetypes
import asyncio
import re
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

# YouTube quality options - Complete list
QUALITIES = {
    "144": "bestvideo[height<=144]+bestaudio/best[height<=144]",
    "240": "bestvideo[height<=240]+bestaudio/best[height<=240]",
    "360": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "1440": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "best": "bestvideo+bestaudio/best",
    "audio": "bestaudio"
}

QUALITY_LABELS = {
    "144": "144p (Lowest)",
    "240": "240p",
    "360": "360p",
    "480": "480p (SD)",
    "720": "720p (HD)",
    "1080": "1080p (Full HD)",
    "1440": "1440p (2K)",
    "2160": "2160p (4K)",
    "best": "🎬 Best Available",
    "audio": "🎵 Audio Only"
}

def get_quality_keyboard():
    """Create quality selection keyboard with all options"""
    keyboard = [
        [InlineKeyboardButton(QUALITY_LABELS["144"], callback_data="144"),
         InlineKeyboardButton(QUALITY_LABELS["240"], callback_data="240")],
        [InlineKeyboardButton(QUALITY_LABELS["360"], callback_data="360"),
         InlineKeyboardButton(QUALITY_LABELS["480"], callback_data="480")],
        [InlineKeyboardButton(QUALITY_LABELS["720"], callback_data="720"),
         InlineKeyboardButton(QUALITY_LABELS["1080"], callback_data="1080")],
        [InlineKeyboardButton(QUALITY_LABELS["1440"], callback_data="1440"),
         InlineKeyboardButton(QUALITY_LABELS["2160"], callback_data="2160")],
        [InlineKeyboardButton(QUALITY_LABELS["best"], callback_data="best"),
         InlineKeyboardButton(QUALITY_LABELS["audio"], callback_data="audio")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🤖 **Welcome to Download Bot**

**I can download:**
• YouTube videos (choose from 9 quality options)
• Any direct download link (http/https)

**How to use:**
1. Send YouTube link → Choose quality from menu
2. Send any direct link → Auto download

**Limits:**
• Max file size: 2GB
• No files stored on server
• Supports all YouTube resolutions up to 4K

Send me a link to start!
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_quality_keyboard()
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links - First get available formats"""
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    message = await update.message.reply_text("🔍 Checking available formats...")
    
    try:
        # First get video info to check available formats
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'listformats': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Store URL and info for later use
            context.user_data['youtube_url'] = url
            context.user_data['video_info'] = {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'formats': info.get('formats', [])
            }
            
            # Get available resolutions
            available_resolutions = set()
            for fmt in info.get('formats', []):
                height = fmt.get('height')
                if height:
                    available_resolutions.add(height)
            
            # Find the best matching quality from our options
            available_qualities = []
            for quality_key in ["144", "240", "360", "480", "720", "1080", "1440", "2160", "best", "audio"]:
                if quality_key == "best" or quality_key == "audio":
                    available_qualities.append(quality_key)
                else:
                    # Check if this resolution is available
                    target_height = int(quality_key)
                    # Check if there's any format with height <= target_height
                    for height in available_resolutions:
                        if height and height <= target_height:
                            available_qualities.append(quality_key)
                            break
            
            # Create custom keyboard based on available qualities
            keyboard = []
            row = []
            
            # Always show best and audio options
            available_qualities.append("best")
            available_qualities.append("audio")
            available_qualities = list(set(available_qualities))  # Remove duplicates
            
            # Sort qualities
            quality_order = ["144", "240", "360", "480", "720", "1080", "1440", "2160", "best", "audio"]
            available_qualities.sort(key=lambda x: quality_order.index(x) if x in quality_order else len(quality_order))
            
            for quality in available_qualities:
                if quality in QUALITY_LABELS:
                    row.append(InlineKeyboardButton(
                        QUALITY_LABELS[quality], 
                        callback_data=quality
                    ))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
            
            if row:  # Add remaining buttons
                keyboard.append(row)
            
            custom_keyboard = InlineKeyboardMarkup(keyboard)
            
            title = info.get('title', 'Unknown')
            duration_sec = info.get('duration', 0)
            duration_min = duration_sec // 60
            
            await message.edit_text(
                f"🎬 **{title}**\n"
                f"⏱️ Duration: {duration_min} minutes\n"
                f"📊 Available qualities:\n"
                f"Select quality:",
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
    
    # Skip YouTube links (they should go to youtube_handler)
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
            
            # Get filename with better extraction
            filename = None
            
            # Try to get from Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                # Try UTF-8 encoded filename first
                utf8_match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
                if utf8_match:
                    import urllib.parse
                    filename = urllib.parse.unquote(utf8_match.group(1))
                else:
                    # Try regular filename
                    regular_match = re.search(r'filename=["\']?([^"\']+)["\']?', content_disposition)
                    if regular_match:
                        filename = regular_match.group(1)
            
            # If not found in header, extract from URL
            if not filename:
                # Extract the last part of URL
                path_part = url.split('?')[0]  # Remove query parameters
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
                    # Don't add extension if already has one
                    if '.' not in filename:
                        filename = filename + ext
                    else:
                        # Check if existing extension matches content type
                        existing_ext = os.path.splitext(filename)[1].lower()
                        if existing_ext != ext.lower():
                            # Replace extension
                            name_part = os.path.splitext(filename)[0]
                            filename = name_part + ext
            
            # Format size for display
            size_mb = total_size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb < 1000 else f"{size_mb/1024:.1f} GB"
            
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
            # Clean up temp file
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
    """Download YouTube video with selected quality"""
    try:
        # Get format string
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
        
        # Add postprocessor for audio
        if quality == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                }],
                'outtmpl': '%(title)s.%(ext)s',
            })
        else:
            ydl_opts.update({
                'merge_output_format': 'mp4',
                'outtmpl': '%(title)s.%(ext)s',
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Video')
            video_id = info.get('id', 'unknown')
            duration = info.get('duration', 0)
            
            # Clean title for filename
            clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            clean_title = clean_title[:100]  # Limit length
            
            # Download to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = os.path.join(tmpdir, f'{clean_title}.%(ext)s')
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_downloader:
                    result = ydl_downloader.extract_info(url, download=True)
                    
                    # Handle playlists (shouldn't happen with noplaylist=True)
                    if 'entries' in result:
                        result = result['entries'][0]
                    
                    # Get the downloaded filename
                    filename = ydl_downloader.prepare_filename(result)
                    
                    # For audio, the filename might have different extension
                    if quality == 'audio' and not os.path.exists(filename):
                        # Look for audio files
                        for ext in ['.m4a', '.mp3', '.opus', '.webm']:
                            possible_file = filename.rsplit('.', 1)[0] + ext
                            if os.path.exists(possible_file):
                                filename = possible_file
                                break
                    
                    # Check if file exists
                    if not os.path.exists(filename):
                        # Search for any downloaded file
                        downloaded_files = [f for f in os.listdir(tmpdir) 
                                          if not f.endswith('.part') and f.endswith(('.mp4', '.m4a', '.webm', '.mkv'))]
                        if downloaded_files:
                            filename = os.path.join(tmpdir, downloaded_files[0])
                        else:
                            return None, "File not found after download"
                    
                    # Read file into buffer
                    buffer = io.BytesIO()
                    with open(filename, 'rb') as f:
                        buffer.write(f.read())
                    
                    buffer.seek(0)
                    
                    # Get file size and extension
                    file_size = buffer.getbuffer().nbytes
                    file_ext = os.path.splitext(filename)[1].lower()
                    if not file_ext:
                        file_ext = '.mp4' if quality != 'audio' else '.m4a'
                    
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
        return None, f"YouTube download failed: {str(e)[:100]}"
    except Exception as e:
        logger.error(f"YouTube processing error: {e}")
        return None, f"Error: {str(e)[:100]}"

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
        size_mb = file_size / (1024 * 1024)
        if size_mb < 1:
            size_str = f"{file_size/1024:.1f} KB"
        elif size_mb < 1000:
            size_str = f"{size_mb:.1f} MB"
        else:
            size_str = f"{size_mb/1024:.1f} GB"
        
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
    print("=" * 50)
    print("🤖 Telegram Download Bot Starting...")
    print(f"📁 Max file size: {MAX_SIZE / (1024**3):.1f} GB")
    print("🎯 YouTube qualities: 144p to 4K + Audio")
    print("🔗 Direct links: Supported")
    print("=" * 50)
    print("Press Ctrl+C to stop the bot")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
