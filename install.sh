#!/bin/bash
# Telegram Download Bot - Complete Installer
# Run: bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)

set -e

echo "=========================================="
echo "  Telegram Download Bot - Complete Install"
echo "=========================================="
echo ""

# Check if already installed
if [ -d "$HOME/telegram-download-bot" ]; then
    echo "❌ Bot already installed at $HOME/telegram-download-bot"
    echo "To reinstall: rm -rf ~/telegram-download-bot"
    exit 1
fi

# Step 1: Update and install dependencies
echo "📦 Installing dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git curl wget ffmpeg

# Step 2: Create directory
echo "📁 Creating bot directory..."
cd ~
rm -rf telegram-download-bot
mkdir telegram-download-bot
cd telegram-download-bot

# Step 3: Create files
echo "📝 Creating files..."

# Create .env
cat > .env << 'EOF'
BOT_TOKEN=your_bot_token_here
OWNER_ID=123456789
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
python-telegram-bot[job-queue]==20.7
yt-dlp>=2024.11.11
python-dotenv>=1.0.0
aiohttp>=3.9.0
requests>=2.31.0
EOF

# Create bot.py with fixed code
cat > bot.py << 'EOF'
#!/usr/bin/env python3
"""
Telegram Download Bot - YouTube + Direct Links
Fixed Version - No FFmpeg Merge Required
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
MAX_SIZE = 2_000_000_000
CHUNK_SIZE = 512 * 1024

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Use single file formats only (no merging required)
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
    "144": "144p", "240": "240p", "360": "360p", "480": "480p",
    "720": "720p", "1080": "1080p", "1440": "1440p", "2160": "2160p",
    "best": "🎬 Best", "audio": "🎵 Audio"
}

def format_file_size(bytes_size):
    if bytes_size == 0: return "0 B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(bytes_size, 1024)))
    return f"{round(bytes_size / math.pow(1024, i), 2)} {size_names[i]}"

def get_quality_keyboard():
    keyboard = [
        [InlineKeyboardButton("144p", callback_data="144"), InlineKeyboardButton("240p", callback_data="240")],
        [InlineKeyboardButton("360p", callback_data="360"), InlineKeyboardButton("480p", callback_data="480")],
        [InlineKeyboardButton("720p", callback_data="720"), InlineKeyboardButton("1080p", callback_data="1080")],
        [InlineKeyboardButton("1440p", callback_data="1440"), InlineKeyboardButton("2160p", callback_data="2160")],
        [InlineKeyboardButton("🎬 Best", callback_data="best"), InlineKeyboardButton("🎵 Audio", callback_data="audio")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Send me a YouTube link or direct download link!",
        reply_markup=get_quality_keyboard()
    )

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    context.user_data['youtube_url'] = url
    await update.message.reply_text("Choose quality:", reply_markup=get_quality_keyboard())

async def direct_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")) or "youtube.com" in url or "youtu.be" in url:
        return
    
    msg = await update.message.reply_text("Downloading...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as response:
                if response.status != 200:
                    await msg.edit_text("❌ Failed")
                    return
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
                downloaded = 0
                
                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded += len(chunk)
                        if downloaded > MAX_SIZE:
                            await msg.edit_text("❌ Too large")
                            temp_file.close()
                            os.unlink(temp_file.name)
                            return
                
                temp_file.close()
                
                filename = url.split('/')[-1].split('?')[0] or "download"
                with open(temp_file.name, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=filename,
                        caption="✅ Downloaded"
                    )
                
                os.unlink(temp_file.name)
                await msg.edit_text("✅ Done!")
                
    except Exception as e:
        await msg.edit_text(f"❌ Error")

def download_youtube_video(url: str, quality: str):
    try:
        ydl_opts = {
            'format': QUALITIES[quality],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([url])
                
                files = [f for f in os.listdir(tmpdir) if not f.endswith('.part')]
                if not files:
                    return None, "No file"
                
                filename = os.path.join(tmpdir, files[0])
                buffer = io.BytesIO()
                with open(filename, 'rb') as f:
                    buffer.write(f.read())
                
                buffer.seek(0)
                file_size = buffer.getbuffer().nbytes
                
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                final_filename = f"{clean_title} - {quality}p.mp4" if quality != 'audio' else f"{clean_title} - audio.m4a"
                
                return buffer, final_filename, title, file_size
                
    except Exception as e:
        return None, str(e)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ Send link first!")
        return
    
    await query.edit_message_text(f"Downloading {quality}...")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_youtube_video, url, quality)
    
    if result[0] is None:
        await query.edit_message_text(f"❌ {result[1]}")
        return
    
    buffer, filename, title, file_size = result
    
    if file_size > MAX_SIZE:
        await query.edit_message_text("❌ Too large")
        buffer.close()
        return
    
    size_str = format_file_size(file_size)
    
    buffer.seek(0)
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buffer,
            filename=filename,
            caption=f"{title} - {quality}\nSize: {size_str}"
        )
        await query.edit_message_text(f"✅ Done! ({size_str})")
    except Exception as e:
        await query.edit_message_text(f"❌ Error")
    finally:
        buffer.close()

def main():
    if not TOKEN:
        print("❌ Add BOT_TOKEN to .env")
        return
    
    app = Application.builder().token(TOKEN).build()
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
    
    print("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
EOF

# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd ~/telegram-download-bot

echo "🤖 Starting Telegram Bot..."
echo ""

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Create: cp .env.example .env"
    echo "Edit: nano .env"
    exit 1
fi

if grep -q "your_bot_token_here" .env; then
    echo "❌ Add your bot token to .env file"
    echo "Get from @BotFather"
    exit 1
fi

# Setup Python
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start
python3 bot.py
EOF

# Create simple manager
cat > bot-manager.sh << 'EOF'
#!/bin/bash
echo "Bot Manager:"
echo "1. Start: ./start.sh"
echo "2. Stop: pkill -f 'python3 bot.py'"
echo "3. Check: ps aux | grep 'python3 bot.py'"
EOF

# Step 4: Setup Python
echo "🐍 Setting up Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 5: Make executable
chmod +x bot.py start.sh bot-manager.sh

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file:"
echo "   nano ~/telegram-download-bot/.env"
echo ""
echo "2. Add your bot token (from @BotFather):"
echo "   BOT_TOKEN=7123456789:AAHdG6v4p8TeH-8hJk9lM2nOp3QrS5tUvWx"
echo ""
echo "3. Start bot:"
echo "   cd ~/telegram-download-bot"
echo "   ./start.sh"
echo ""
echo "🚀 Bot is ready!"
