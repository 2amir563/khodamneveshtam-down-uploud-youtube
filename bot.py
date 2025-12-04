#!/usr/bin/env python3
"""
Telegram Download Bot
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
MAX_SIZE = 2_000_000_000
CHUNK_SIZE = 512 * 1024

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

QUALITY_OPTIONS = {
    "best": {"format": "best", "label": "Best Quality", "ext": "mp4"},
    "720": {"format": "best[height<=720]", "label": "720p", "ext": "mp4"},
    "480": {"format": "best[height<=480]", "label": "480p", "ext": "mp4"},
    "audio": {"format": "bestaudio", "label": "Audio Only", "ext": "m4a"}
}

def create_quality_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎬 Best", callback_data="best"),
         InlineKeyboardButton("📺 720p", callback_data="720")],
        [InlineKeyboardButton("📱 480p", callback_data="480"),
         InlineKeyboardButton("🎵 Audio", callback_data="audio")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """
🤖 Welcome to Download Bot

I can download:
• YouTube videos (choose quality)
• Any direct link (http/https)

How to use:
1. Send YouTube link → Choose quality
2. Send direct link → Auto download

Max file size: 2GB
"""
    await update.message.reply_text(welcome, reply_markup=create_quality_keyboard())

async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "youtube.com" in url or "youtu.be" in url:
        context.user_data['youtube_url'] = url
        await update.message.reply_text("Choose quality:", reply_markup=create_quality_keyboard())

async def handle_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        return
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    msg = await update.message.reply_text("Checking...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as resp:
                if resp.status != 200:
                    await msg.edit_text("Invalid link")
                    return
        
        await msg.edit_text("Downloading...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                if resp.status != 200:
                    await msg.edit_text("Failed")
                    return
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
                downloaded = 0
                
                async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded += len(chunk)
                        if downloaded > MAX_SIZE:
                            await msg.edit_text("Too large (max 2GB)")
                            temp_file.close()
                            os.unlink(temp_file.name)
                            return
                
                temp_file.close()
                
                filename = url.split('/')[-1].split('?')[0] or "download"
                ext = mimetypes.guess_extension(resp.headers.get('Content-Type', '')) or ''
                if ext and not filename.endswith(ext):
                    filename += ext
                
                with open(temp_file.name, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=filename,
                        caption="✅ Downloaded",
                        read_timeout=300,
                        write_timeout=300
                    )
                
                os.unlink(temp_file.name)
                await msg.edit_text("✅ Done!")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"Error: {str(e)[:100]}")

def download_youtube_video(url: str, quality: str):
    try:
        opts = QUALITY_OPTIONS[quality]
        ydl_opts = {'format': opts['format'], 'quiet': True, 'noplaylist': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{opts["ext"]}') as tmp:
                ydl_opts['outtmpl'] = tmp.name
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([url])
                
                buffer = io.BytesIO()
                with open(tmp.name, 'rb') as f:
                    buffer.write(f.read())
                os.unlink(tmp.name)
            
            buffer.seek(0)
            filename = f"{info.get('id', 'video')}.{opts['ext']}"
            return buffer, filename, title
            
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        return None, str(e)

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get("youtube_url")
    
    if not url:
        await query.edit_message_text("No YouTube link")
        return
    
    await query.edit_message_text(f"Downloading {quality}...")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_youtube_video, url, quality)
    
    if result[0] is None:
        await query.edit_message_text(f"Failed: {result[1]}")
        return
    
    buffer, filename, title = result
    
    if buffer.getbuffer().nbytes > MAX_SIZE:
        await query.edit_message_text("Too large (max 2GB)")
        buffer.close()
        return
    
    buffer.seek(0)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=buffer,
        filename=filename,
        caption=f"✅ {title} - {quality}",
        read_timeout=300,
        write_timeout=300
    )
    
    buffer.close()
    await query.edit_message_text("✅ Done!")

def main():
    if not TOKEN:
        print("ERROR: Add BOT_TOKEN to .env file")
        print("Edit: nano ~/telegram-download-bot/.env")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND, handle_youtube))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^https?://') & ~filters.Regex(r'youtube\.com|youtu\.be') & ~filters.COMMAND, handle_direct))
    app.add_handler(CallbackQueryHandler(handle_quality))
    
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
