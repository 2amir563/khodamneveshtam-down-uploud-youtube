
### **2. `install.sh** (اصلی - همان یک دستور)

```bash
#!/bin/bash
# One-Command Installer for Telegram Download Bot
# Run: bash <(curl -s https://raw.githubusercontent.com/2amir563/telegram-download-bot/main/install.sh)

set -e

echo "=========================================="
echo "  Telegram Download Bot - One Click Install"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Step 1: Check if already installed
print_step "Checking system..."
if [ -d "$HOME/telegram-download-bot" ]; then
    print_error "Bot already installed at $HOME/telegram-download-bot"
    echo "To reinstall, run: rm -rf ~/telegram-download-bot"
    exit 1
fi

# Step 2: Update system
print_step "Updating system packages..."
sudo apt update -y > /dev/null 2>&1

# Step 3: Install dependencies
print_step "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git curl wget ffmpeg > /dev/null 2>&1

# Step 4: Create directory
print_step "Creating bot directory..."
cd ~
mkdir telegram-download-bot
cd telegram-download-bot

# Step 5: Create all necessary files
print_step "Creating bot files..."

# Create .env file
cat > .env << 'EOF'
# Telegram Bot Configuration
# Get token from @BotFather on Telegram
BOT_TOKEN=your_bot_token_here

# Your Telegram User ID (optional)
# Send /id to @userinfobot to get your ID
OWNER_ID=123456789
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
python-telegram-bot[job-queue]==20.7
yt-dlp>=2024.11.11
python-dotenv>=1.0.0
aiohttp>=3.9.0
EOF

# Create the main bot.py file
cat > bot.py << 'EOF'
#!/usr/bin/env python3
"""
Telegram Download Bot
Downloads YouTube videos and direct links without saving to disk
"""

import os
import io
import logging
import tempfile
import mimetypes
import asyncio
from typing import Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import yt_dlp
import aiohttp

# Load environment
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID", "0")

# Constants
MAX_FILE_SIZE = 2_000_000_000  # 2GB
CHUNK_SIZE = 512 * 1024  # 512KB

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# YouTube quality settings
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
    welcome_text = """
🤖 Welcome to Download Bot

I can download:
• YouTube videos (choose quality)
• Any direct download link

How to use:
1. Send YouTube link → Choose quality
2. Send direct link → Auto download

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
    url = update.message.text.strip()
    
    if not ("youtube.com" in url or "youtu.be" in url):
        return
    
    context.user_data['youtube_url'] = url
    
    await update.message.reply_text(
        "Select download quality:",
        reply_markup=create_quality_keyboard()
    )

async def handle_direct_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        return
    
    if "youtube.com" in url or "youtu.be" in url:
        return
    
    message = await update.message.reply_text("Checking link...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as response:
                if response.status != 200:
                    await message.edit_text("Invalid link")
                    return
                
                size = int(response.headers.get('Content-Length', 0))
                if size > MAX_FILE_SIZE:
                    await message.edit_text("File too large (max 2GB)")
                    return
        
        await message.edit_text("Downloading...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as response:
                if response.status != 200:
                    await message.edit_text("Download failed")
                    return
                
                # Create temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
                
                try:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            if downloaded > MAX_FILE_SIZE:
                                await message.edit_text("File too large")
                                temp_file.close()
                                os.unlink(temp_file.name)
                                return
                    
                    temp_file.close()
                    
                    # Get filename
                    filename = url.split('/')[-1].split('?')[0] or "download"
                    content_type = response.headers.get('Content-Type', '')
                    if content_type:
                        ext = mimetypes.guess_extension(content_type)
                        if ext and not filename.endswith(ext):
                            filename += ext
                    
                    # Upload to Telegram
                    with open(temp_file.name, 'rb') as file:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=file,
                            filename=filename,
                            caption="Downloaded",
                            read_timeout=300,
                            write_timeout=300
                        )
                    
                    await message.edit_text("Done!")
                    
                finally:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.edit_text(f"Error: {str(e)[:100]}")

def download_youtube_video(url: str, quality: str):
    try:
        quality_info = QUALITY_OPTIONS[quality]
        
        ydl_opts = {
            'format': quality_info['format'],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            video_id = info.get('id', 'unknown')
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{quality_info["ext"]}') as tmp:
                ydl_opts['outtmpl'] = tmp.name
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                    ydl_dl.download([url])
                
                # Read to buffer
                buffer = io.BytesIO()
                with open(tmp.name, 'rb') as f:
                    buffer.write(f.read())
                
                os.unlink(tmp.name)
            
            buffer.seek(0)
            filename = f"{video_id}.{quality_info['ext']}"
            
            return buffer, filename, title
            
    except Exception as e:
        logger.error(f"YouTube error: {e}")
        return None, f"Error: {str(e)}"

async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("No YouTube link found")
        return
    
    await query.edit_message_text(f"Downloading {quality}...")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_youtube_video, url, quality)
    
    if result[0] is None:
        await query.edit_message_text(f"Failed: {result[1]}")
        return
    
    buffer, filename, title = result
    
    if buffer.getbuffer().nbytes > MAX_FILE_SIZE:
        await query.edit_message_text("File too large")
        buffer.close()
        return
    
    buffer.seek(0)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=buffer,
        filename=filename,
        caption=f"{title} - {quality}",
        read_timeout=300,
        write_timeout=300
    )
    
    buffer.close()
    await query.edit_message_text("Done!")

def main():
    if not TOKEN:
        logger.error("No BOT_TOKEN in .env file!")
        print("Please add your bot token to .env file")
        print("Edit: nano ~/telegram-download-bot/.env")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        handle_youtube_link
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^https?://') & 
        ~filters.Regex(r'(youtube\.com|youtu\.be)') & 
        ~filters.COMMAND,
        handle_direct_link
    ))
    
    app.add_handler(CallbackQueryHandler(handle_quality_selection))
    
    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
EOF

# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# Check .env
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Create it: cp .env.example .env"
    echo "Then edit: nano .env"
    exit 1
fi

# Check token
if grep -q "your_bot_token_here" .env; then
    echo "ERROR: Please edit .env file!"
    echo "Add your bot token from @BotFather"
    echo "Command: nano .env"
    exit 1
fi

# Setup virtual environment
if [ ! -d "venv" ]; then
    echo "Setting up Python environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Start bot
source venv/bin/activate
echo "Starting bot..."
python3 bot.py
EOF

# Create service-setup.sh
cat > service-setup.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

SERVICE_FILE="/etc/systemd/system/telegram-download-bot.service"

echo "Installing systemd service..."

# Create service file
cat > $SERVICE_FILE << SERVICE
[Unit]
Description=Telegram Download Bot
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:\\\$PATH"
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Enable service
systemctl daemon-reload
systemctl enable telegram-download-bot

echo ""
echo "Service installed!"
echo ""
echo "Commands:"
echo "  Start:  systemctl start telegram-download-bot"
echo "  Stop:   systemctl stop telegram-download-bot"
echo "  Status: systemctl status telegram-download-bot"
echo "  Logs:   journalctl -u telegram-download-bot -f"
echo ""
echo "To start: systemctl start telegram-download-bot"
EOF

# Create uninstall.sh
cat > uninstall.sh << 'EOF'
#!/bin/bash
echo "Uninstalling Telegram Download Bot..."
echo ""

# Stop bot
pkill -f "python3 bot.py" 2>/dev/null && echo "Bot stopped."

# Remove service if exists
if [ -f "/etc/systemd/system/telegram-download-bot.service" ]; then
    echo "Removing systemd service..."
    systemctl stop telegram-download-bot.service 2>/dev/null
    systemctl disable telegram-download-bot.service 2>/dev/null
    rm -f /etc/systemd/system/telegram-download-bot.service
    systemctl daemon-reload
fi

# Remove directory
read -p "Remove bot directory? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ~
    rm -rf telegram-download-bot
    echo "Directory removed."
fi

echo ""
echo "Uninstall complete!"
echo "To remove Python packages: pip3 uninstall python-telegram-bot yt-dlp"
EOF

# Make all scripts executable
chmod +x bot.py start.sh service-setup.sh uninstall.sh

# Step 6: Setup Python environment
print_step "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

print_success "Installation complete!"
echo ""
echo "=========================================="
echo "📋 NEXT STEPS:"
echo "=========================================="
echo ""
echo "1. Edit the configuration file:"
echo "   nano ~/telegram-download-bot/.env"
echo ""
echo "2. Add your bot token (get from @BotFather):"
echo "   BOT_TOKEN=7123456789:AAHdG6v4p8TeH-8hJk9lM2nOp3QrS5tUvWx"
echo ""
echo "3. Start the bot:"
echo "   cd ~/telegram-download-bot"
echo "   ./start.sh"
echo ""
echo "4. (Optional) Run as background service:"
echo "   sudo ./service-setup.sh"
echo "   sudo systemctl start telegram-download-bot"
echo ""
echo "=========================================="
echo "📞 To stop the bot: Press Ctrl+C"
echo "🗑️  To uninstall: ./uninstall.sh"
echo "=========================================="
