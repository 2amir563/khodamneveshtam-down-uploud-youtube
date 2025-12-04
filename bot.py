#!/usr/bin/env python3
"""
Simple YouTube Download Bot - Fixed Version
"""

import os
import io
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple quality options
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
    await update.message.reply_text(
        "Send me a YouTube link!",
        reply_markup=get_keyboard()
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "youtube.com" in url or "youtu.be" in url:
        context.user_data['url'] = url
        await update.message.reply_text("Choose quality:", reply_markup=get_keyboard())

def download_video_simple(url: str, quality: str):
    """Simple YouTube download function"""
    try:
        ydl_opts = {
            'format': QUALITIES[quality],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'outtmpl': '-',  # Output to stdout
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            video_id = info.get('id', 'unknown')
            
            # Create a buffer
            buffer = io.BytesIO()
            
            # Download using different approach
            import subprocess
            import json
            
            # Get download URL
            result = ydl.extract_info(url, download=False)
            formats = result.get('formats', [])
            
            if not formats:
                return None, "No formats available"
            
            # Find best format
            if quality == 'audio':
                # Find audio format
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                if audio_formats:
                    format_id = audio_formats[0]['format_id']
                else:
                    # Fallback to any format with audio
                    format_id = 'bestaudio'
            else:
                format_id = QUALITIES[quality]
            
            # Download with yt-dlp directly
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    info_dict = ydl2.extract_info(url, download=True)
                    filename = ydl2.prepare_filename(info_dict)
                    
                    # If it's a playlist, get the first entry
                    if 'entries' in info_dict:
                        info_dict = info_dict['entries'][0]
                        filename = ydl2.prepare_filename(info_dict)
                    
                    # Read the file
                    if os.path.exists(filename):
                        with open(filename, 'rb') as f:
                            buffer.write(f.read())
                        
                        buffer.seek(0)
                        
                        # Get extension
                        ext = filename.split('.')[-1] if '.' in filename else 'mp4'
                        if quality == 'audio' and ext == 'webm':
                            ext = 'm4a'
                        
                        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        filename_out = f"{clean_title[:30]}.{ext}"
                        
                        return buffer, filename_out, title
                    else:
                        return None, "File not downloaded"
                        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None, str(e)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("Send YouTube link first!")
        return
    
    await query.edit_message_text(f"Downloading {quality}...")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_video_simple, url, quality)
    
    if result[0] is None:
        await query.edit_message_text(f"Failed: {result[1]}")
        return
    
    buffer, filename, title = result
    
    # Check size (max 50MB for testing)
    if buffer.getbuffer().nbytes > 50_000_000:
        await query.edit_message_text("Video too large for test")
        buffer.close()
        return
    
    buffer.seek(0)
    
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buffer,
            filename=filename,
            caption=f"{title} - {quality}",
            read_timeout=60,
            write_timeout=60
        )
        await query.edit_message_text("✅ Done!")
    except Exception as e:
        await query.edit_message_text(f"Upload error: {str(e)[:100]}")
    finally:
        buffer.close()

def main():
    if not TOKEN:
        print("ERROR: No BOT_TOKEN in .env")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        youtube_handler
    ))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
