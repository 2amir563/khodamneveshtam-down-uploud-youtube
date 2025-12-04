#!/usr/bin/env python3
"""
Telegram Download Bot - Fixed YouTube Download
GitHub: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube
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

# YouTube quality settings - FIXED FORMATS
QUALITY_OPTIONS = {
    "best": {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "label": "Best Quality",
        "ext": "mp4"
    },
    "720": {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "label": "720p HD",
        "ext": "mp4"
    },
    "480": {
        "format": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
        "label": "480p",
        "ext": "mp4"
    },
    "audio": {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "label": "Audio Only",
        "ext": "m4a"
    }
}

def create_quality_keyboard():
    """Create quality selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🎬 Best", callback_data="best"),
            InlineKeyboardButton("📺 720p", callback_data="720"),
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data="480"),
            InlineKeyboardButton("🎵 Audio", callback_data="audio"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🤖 Welcome to Download Bot

I can download:
• YouTube videos (choose quality)
• Any direct download link (http/https)

How to use:
1. Send YouTube link → I'll ask for quality
2. Send any direct link → Auto download

Limits:
• Max file size: 2GB
• No files stored on server

Send me a link to start!
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_quality_keyboard()
    )

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links"""
    url = update.message.text.strip()
    
    # Validate URL
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    # Store URL for later use
    context.user_data['youtube_url'] = url
    
    # Ask for quality
    await update.message.reply_text(
        "🎯 Select download quality:",
        reply_markup=create_quality_keyboard()
    )

async def handle_direct_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links"""
    url = update.message.text.strip()
    
    # Validate URL
    if not url.startswith(("http://", "https://")):
        return
    
    # Check if it's a YouTube link (should be handled separately)
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("🔍 Checking link...")
    
    try:
        # Check file size first
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as response:
                if response.status != 200:
                    await message.edit_text("❌ Invalid link or server error")
                    return
                
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size = int(content_length)
                    if size > MAX_SIZE:
                        await message.edit_text("❌ File is too large (max 2GB)")
                        return
        
        await message.edit_text("⬇️ Downloading...")
        
        # Download and stream
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as response:
                if response.status != 200:
                    await message.edit_text("❌ Download failed")
                    return
                
                # Get filename
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = None
                
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"\'').split(';')[0]
                
                if not filename:
                    # Extract from URL
                    filename = url.split('/')[-1].split('?')[0]
                    if not filename or filename == '':
                        filename = "download"
                
                # Add extension if missing
                content_type = response.headers.get('Content-Type', '')
                if content_type:
                    ext = mimetypes.guess_extension(content_type)
                    if ext and not filename.endswith(ext):
                        filename += ext
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
                
                try:
                    # Download in chunks
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            if downloaded > MAX_SIZE:
                                await message.edit_text("❌ File is too large (max 2GB)")
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
                            caption=f"✅ Downloaded successfully\n🔗 {url[:50]}...",
                            read_timeout=300,
                            write_timeout=300,
                            connect_timeout=300
                        )
                    
                    await message.edit_text("✅ Upload complete!")
                    
                finally:
                    # Cleanup
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                        
    except asyncio.TimeoutError:
        await message.edit_text("❌ Connection timeout")
    except Exception as e:
        logger.error(f"Direct download error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

def download_youtube_video(url: str, quality: str):
    """Download YouTube video to memory buffer - FIXED VERSION"""
    try:
        quality_info = QUALITY_OPTIONS[quality]
        
        # yt-dlp options
        ydl_opts = {
            'format': quality_info['format'],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'no_color': True,
            'outtmpl': '%(title)s.%(ext)s',
            'merge_output_format': 'mp4' if quality != 'audio' else None,
        }
        
        # Add postprocessor for audio extraction
        if quality == 'audio':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id', 'unknown')
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            # Clean title for filename
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # Create temporary directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts['outtmpl'] = os.path.join(temp_dir, f'%(title)s.%(ext)s')
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_downloader:
                    ydl_downloader.download([url])
                
                # Find the downloaded file
                downloaded_files = [f for f in os.listdir(temp_dir) if f.endswith(('.mp4', '.m4a', '.webm'))]
                if not downloaded_files:
                    return None, "No video file found after download"
                
                video_file = os.path.join(temp_dir, downloaded_files[0])
                
                # Read file into buffer
                buffer = io.BytesIO()
                with open(video_file, 'rb') as f:
                    buffer.write(f.read())
                
                buffer.seek(0)
                
                # Create filename
                filename = f"{clean_title[:50]}_{quality}.{quality_info['ext']}".replace(' ', '_')
                
                return buffer, filename, title
                
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"YouTube download error: {e}")
        return None, f"YouTube download failed: {str(e)[:100]}"
    except Exception as e:
        logger.error(f"General error: {e}")
        return None, f"Error: {str(e)[:100]}"

async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection from inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ No YouTube link found. Send a link first.")
        return
    
    if quality not in QUALITY_OPTIONS:
        await query.edit_message_text("❌ Invalid quality selection")
        return
    
    await query.edit_message_text(f"⬇️ Downloading ({QUALITY_OPTIONS[quality]['label']})...")
    
    try:
        # Download video in thread (to avoid blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_youtube_video, url, quality)
        
        if result[0] is None:
            error_msg = result[1]
            await query.edit_message_text(f"❌ {error_msg}")
            return
        
        buffer, filename, title = result
        
        # Check size
        file_size = buffer.getbuffer().nbytes
        if file_size > MAX_SIZE:
            await query.edit_message_text("❌ File is too large (max 2GB)")
            buffer.close()
            return
        
        # Send to Telegram
        buffer.seek(0)
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buffer,
            filename=filename,
            caption=f"✅ {title}\n🎯 Quality: {QUALITY_OPTIONS[quality]['label']}",
            read_timeout=300,
            write_timeout=300,
            connect_timeout=300
        )
        
        buffer.close()
        await query.edit_message_text("✅ Upload complete!")
        
    except Exception as e:
        logger.error(f"YouTube processing error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)[:100]}")

def main():
    """Start the bot"""
    if not TOKEN:
        logger.error("ERROR: BOT_TOKEN not found in .env file!")
        print("Please add your bot token to the .env file:")
        print("BOT_TOKEN=your_token_here")
        return
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    
    # YouTube links handler
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        handle_youtube_link
    ))
    
    # Direct links handler (not YouTube)
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^https?://') & 
        ~filters.Regex(r'(youtube\.com|youtu\.be)') & 
        ~filters.COMMAND,
        handle_direct_link
    ))
    
    # Quality selection handler
    app.add_handler(CallbackQueryHandler(handle_quality_selection))
    
    # Error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
    
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot is starting...")
    print("🤖 Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
