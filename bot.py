#!/usr/bin/env python3
"""
Complete Telegram Download Bot - YouTube + Direct Links
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

# YouTube quality options
QUALITIES = {
    "best": "bestvideo+bestaudio/best",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "audio": "bestaudio"
}

def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎬 Best", callback_data="best"),
         InlineKeyboardButton("📺 720p", callback_data="720")],
        [InlineKeyboardButton("📱 480p", callback_data="480"),
         InlineKeyboardButton("🎵 Audio", callback_data="audio")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 Welcome to Download Bot

I can download:
• YouTube videos (choose quality)
• Any direct download link (http/https)

How to use:
1. Send YouTube link → Choose quality
2. Send any direct link → Auto download

Limits:
• Max file size: 2GB
• No files stored on server

Send me a link to start!
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_keyboard()
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links"""
    url = update.message.text.strip()
    if "youtube.com" in url or "youtu.be" in url:
        context.user_data['youtube_url'] = url
        await update.message.reply_text("Choose quality:", reply_markup=get_keyboard())

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
        except:
            # If HEAD fails, try with GET but limit download
            pass
        
        await message.edit_text("⬇️ Downloading...")
        
        # Download the file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
        
        try:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Check size during download
                    if downloaded > MAX_SIZE:
                        await message.edit_text("❌ File too large (max 2GB)")
                        temp_file.close()
                        os.unlink(temp_file.name)
                        return
            
            temp_file.close()
            
            # Get filename
            filename = None
            
            # Try to get from Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                import re
                match = re.search(r'filename\*?=["\']?(?:UTF-\d["\']*)?([^"\']+)["\']?', content_disposition)
                if match:
                    filename = match.group(1)
                else:
                    # Simple extraction
                    filename = content_disposition.split('filename=')[1].strip('"\'')
            
            # If not found in header, extract from URL
            if not filename:
                filename = url.split('/')[-1].split('?')[0]
                if not filename or filename == '':
                    filename = "download"
            
            # Add proper extension
            content_type = response.headers.get('Content-Type', '')
            if content_type:
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    # Remove any existing extension and add correct one
                    if '.' in filename:
                        name_part = filename.rsplit('.', 1)[0]
                        filename = name_part + ext
                    else:
                        filename = filename + ext
            
            # Send to Telegram
            with open(temp_file.name, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=filename,
                    caption=f"✅ Downloaded\n🔗 {url[:50]}...",
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=300
                )
            
            await message.edit_text("✅ Upload complete!")
            
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
    """Download YouTube video"""
    try:
        ydl_opts = {
            'format': QUALITIES[quality],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'outtmpl': '-',  # Output to stdout
        }
        
        # Add postprocessor for audio
        if quality == 'audio':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            
            # Download to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    info_dict = ydl2.extract_info(url, download=True)
                    filename = ydl2.prepare_filename(info_dict)
                    
                    # Handle playlists
                    if 'entries' in info_dict:
                        info_dict = info_dict['entries'][0]
                        filename = ydl2.prepare_filename(info_dict)
                    
                    # Check if file exists
                    if not os.path.exists(filename):
                        # Try with different extension
                        possible_files = [f for f in os.listdir(tmpdir) if not f.endswith('.part')]
                        if possible_files:
                            filename = os.path.join(tmpdir, possible_files[0])
                        else:
                            return None, "File not found after download"
                    
                    # Read file into buffer
                    buffer = io.BytesIO()
                    with open(filename, 'rb') as f:
                        buffer.write(f.read())
                    
                    buffer.seek(0)
                    
                    # Prepare filename for Telegram
                    ext = filename.split('.')[-1] if '.' in filename else 'mp4'
                    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    filename_out = f"{clean_title[:30]}.{ext}"
                    
                    return buffer, filename_out, title
                    
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None, str(e)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ Send YouTube link first!")
        return
    
    await query.edit_message_text(f"⬇️ Downloading {quality}...")
    
    # Download in background thread
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_youtube_video, url, quality)
    
    if result[0] is None:
        await query.edit_message_text(f"❌ Failed: {result[1]}")
        return
    
    buffer, filename, title = result
    
    # Check size
    if buffer.getbuffer().nbytes > MAX_SIZE:
        await query.edit_message_text("❌ Video too large (max 2GB)")
        buffer.close()
        return
    
    buffer.seek(0)
    
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buffer,
            filename=filename,
            caption=f"{title} - {quality}",
            read_timeout=300,
            write_timeout=300,
            connect_timeout=300
        )
        await query.edit_message_text("✅ Done!")
    except Exception as e:
        await query.edit_message_text(f"❌ Upload error: {str(e)[:100]}")
    finally:
        buffer.close()

def main():
    if not TOKEN:
        print("ERROR: No BOT_TOKEN in .env file!")
        print("Edit: nano ~/telegram-download-bot/.env")
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
    
    # Start the bot
    print("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
