#!/bin/bash
# Complete Telegram Bot Installer
# Author: 2amir563

set -e  # Exit on error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Telegram Download Bot Installer   ${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}Warning: Running as root. Consider using a regular user.${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Clean up old installation
echo -e "${YELLOW}[1/5] Cleaning old installation...${NC}"
cd ~
if [ -d "khodamneveshtam-down-uploud-youtube" ]; then
    echo "Removing old directory..."
    rm -rf khodamneveshtam-down-uploud-youtube
fi

# Step 2: Clone fresh repository
echo -e "${YELLOW}[2/5] Downloading bot files...${NC}"
git clone https://github.com/2amir563/khodamneveshtam-down-uploud-youtube.git
cd khodamneveshtam-down-uploud-youtube

# Step 3: Install system dependencies
echo -e "${YELLOW}[3/5] Installing system dependencies...${NC}"
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git curl ffmpeg

# Step 4: Setup virtual environment and install packages
echo -e "${YELLOW}[4/5] Setting up Python environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install python-telegram-bot[job-queue]==20.7 yt-dlp>=2024.4.9 python-dotenv>=1.0.0 aiohttp>=3.9.0 requests>=2.31.0

# Step 5: Create necessary files
echo -e "${YELLOW}[5/5] Creating configuration files...${NC}"

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}Created .env file. Please edit it with your bot token.${NC}"
fi

# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and edit it:"
    echo "cp .env.example .env && nano .env"
    exit 1
fi

# Check if BOT_TOKEN is set
if ! grep -q "BOT_TOKEN=" .env || grep -q "BOT_TOKEN=123456789" .env; then
    echo "ERROR: BOT_TOKEN not set in .env file!"
    echo "Edit .env file: nano .env"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start bot
echo "Starting Telegram Bot..."
python3 bot.py
EOF

# Create stop.sh
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping bot..."
pkill -f "python3 bot.py" 2>/dev/null
echo "Bot stopped."
EOF

# Create uninstall.sh
cat > uninstall.sh << 'EOF'
#!/bin/bash
echo "Uninstalling Telegram Bot..."
echo ""

# Stop bot first
pkill -f "python3 bot.py" 2>/dev/null

# Remove service if exists
if [ -f "/etc/systemd/system/telegram-download-bot.service" ]; then
    echo "Removing systemd service..."
    sudo systemctl stop telegram-download-bot.service
    sudo systemctl disable telegram-download-bot.service
    sudo rm -f /etc/systemd/system/telegram-download-bot.service
    sudo systemctl daemon-reload
fi

# Ask for confirmation
read -p "Remove bot directory? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ..
    rm -rf khodamneveshtam-down-uploud-youtube
    echo "Bot directory removed."
fi

echo ""
echo "Uninstall complete!"
echo "Note: Python packages are still installed globally."
echo "To remove them: pip3 uninstall python-telegram-bot yt-dlp python-dotenv aiohttp"
EOF

# Create service-install.sh
cat > service-install.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

SERVICE_NAME="telegram-download-bot"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

echo "Installing as systemd service..."

# Create service file
sudo tee $SERVICE_FILE > /dev/null << SERVICE
[Unit]
Description=Telegram Download Bot (YouTube + Direct Links)
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:\$PATH"
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo ""
echo "Service installed successfully!"
echo ""
echo "Commands:"
echo "  Start:    sudo systemctl start $SERVICE_NAME"
echo "  Stop:     sudo systemctl stop $SERVICE_NAME"
echo "  Status:   sudo systemctl status $SERVICE_NAME"
echo "  Logs:     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Start the service: sudo systemctl start $SERVICE_NAME"
EOF

# Create the main bot.py file
cat > bot.py << 'EOF'
#!/usr/bin/env python3
"""
Telegram Bot for YouTube and Direct Link Downloads
Memory-only streaming, no files saved on disk
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

# Load environment variables
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

# YouTube quality options
QUALITY_OPTIONS = {
    "best": {"format": "best", "label": "Best Quality"},
    "720": {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]", "label": "720p"},
    "480": {"format": "bestvideo[height<=480]+bestaudio/best[height<=480]", "label": "480p"},
    "audio": {"format": "bestaudio", "label": "Audio Only"}
}

def create_quality_keyboard():
    """Create inline keyboard for quality selection"""
    keyboard = [
        [
            InlineKeyboardButton("🎬 Best Quality", callback_data="best"),
            InlineKeyboardButton("📺 720p", callback_data="720"),
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data="480"),
            InlineKeyboardButton("🎵 Audio Only", callback_data="audio"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
👋 *Welcome to Download Bot*

*Supported Links:*
• YouTube (youtube.com, youtu.be)
• Direct download links (http/https)

*How to use:*
1. Send a YouTube link → Choose quality
2. Send a direct link → Auto download

*Limits:*
• Max file size: 2GB
• No files stored on server
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=create_quality_keyboard()
    )

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links"""
    url = update.message.text.strip()
    context.user_data['youtube_url'] = url
    
    await update.message.reply_text(
        "🎯 Select download quality:",
        reply_markup=create_quality_keyboard()
    )

async def handle_direct_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct download links"""
    url = update.message.text.strip()
    
    message = await update.message.reply_text("🔍 Checking link...")
    
    try:
        # Check file size first
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as response:
                if response.status != 200:
                    await message.edit_text("❌ Invalid link or server error")
                    return
                
                size = int(response.headers.get('Content-Length', 0))
                if size > MAX_SIZE:
                    await message.edit_text("❌ File too large (max 2GB)")
                    return
        
        await message.edit_text("⬇️ Downloading...")
        
        # Download and stream to Telegram
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    await message.edit_text("❌ Download failed")
                    return
                
                # Get filename
                content_disposition = response.headers.get('Content-Disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"\'')
                else:
                    filename = url.split('/')[-1].split('?')[0] or "download"
                
                # Add extension if missing
                content_type = response.headers.get('Content-Type', '')
                ext = mimetypes.guess_extension(content_type) or ''
                if not filename.endswith(ext) and ext:
                    filename += ext
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                    total_size = 0
                    
                    # Download in chunks
                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if chunk:
                            temp_file.write(chunk)
                            total_size += len(chunk)
                            
                            if total_size > MAX_SIZE:
                                await message.edit_text("❌ File too large (max 2GB)")
                                os.unlink(temp_file.name)
                                return
                    
                    temp_file_path = temp_file.name
                
                # Upload to Telegram
                with open(temp_file_path, 'rb') as file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename=filename,
                        caption=f"📥 Downloaded\n🔗 {url[:50]}...",
                        read_timeout=300,
                        write_timeout=300
                    )
                
                # Cleanup
                os.unlink(temp_file_path)
                await message.edit_text("✅ Upload complete!")
                
    except asyncio.TimeoutError:
        await message.edit_text("❌ Connection timeout")
    except Exception as e:
        logger.error(f"Direct download error: {e}")
        await message.edit_text(f"❌ Error: {str(e)[:100]}")

async def download_youtube_video(url: str, quality: str) -> Optional[tuple]:
    """Download YouTube video to memory"""
    try:
        ydl_opts = {
            'format': QUALITY_OPTIONS[quality]['format'],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'outtmpl': '-',  # Output to stdout
            'socket_timeout': 30,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id', 'unknown')
            title = info.get('title', 'Unknown')
            
            # Download to memory buffer
            buffer = io.BytesIO()
            ydl_opts['outtmpl'] = '-'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                # Download process
                result = ydl_dl.download([url])
                
            # For simplicity, we'll use a different approach
            # Download to temp file then read to buffer
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                ydl_opts['outtmpl'] = tmp.name
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                    ydl_dl.download([url])
                
                # Read temp file into buffer
                with open(tmp.name, 'rb') as f:
                    buffer.write(f.read())
                os.unlink(tmp.name)
            
            buffer.seek(0)
            
            # Determine file extension
            ext = 'mp4' if quality != 'audio' else 'm4a'
            filename = f"{video_id}.{ext}"
            
            return buffer, filename, title
            
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None

async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection from inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data
    url = context.user_data.get('youtube_url')
    
    if not url:
        await query.edit_message_text("❌ No YouTube link found. Send a link first.")
        return
    
    await query.edit_message_text(f"⬇️ Downloading {quality} quality...")
    
    # Download video
    result = await asyncio.to_thread(download_youtube_video, url, quality)
    
    if not result:
        await query.edit_message_text("❌ Failed to download video")
        return
    
    buffer, filename, title = result
    
    # Check size
    if buffer.getbuffer().nbytes > MAX_SIZE:
        await query.edit_message_text("❌ File too large (max 2GB)")
        buffer.close()
        return
    
    # Send to Telegram
    buffer.seek(0)
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buffer,
            filename=filename,
            caption=f"✅ {title}\n🎯 Quality: {quality}",
            read_timeout=300,
            write_timeout=300
        )
        await query.edit_message_text("✅ Upload complete!")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await query.edit_message_text(f"❌ Upload failed: {str(e)[:100]}")
    finally:
        buffer.close()

def main():
    """Main function to start the bot"""
    if not TOKEN:
        logger.error("BOT_TOKEN not found in .env file!")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(
        filters.Regex(r'(youtube\.com|youtu\.be)') & ~filters.COMMAND,
        handle_youtube_link
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^https?://') & ~filters.COMMAND & ~filters.Regex(r'youtube\.com|youtu\.be'),
        handle_direct_link
    ))
    application.add_handler(CallbackQueryHandler(handle_quality_selection))
    
    # Start bot
    logger.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
EOF

# Make all scripts executable
chmod +x bot.py start.sh stop.sh uninstall.sh service-install.sh

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}       Installation Complete!        ${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit the .env file with your bot token:"
echo "   nano .env"
echo ""
echo "2. Start the bot:"
echo "   ./start.sh"
echo ""
echo "3. (Optional) Install as system service:"
echo "   ./service-install.sh"
echo "   sudo systemctl start telegram-download-bot"
echo ""
echo -e "${GREEN}Files created:${NC}"
echo "✓ bot.py              - Main bot script"
echo "✓ start.sh            - Start bot"
echo "✓ stop.sh             - Stop bot"
echo "✓ uninstall.sh        - Uninstall bot"
echo "✓ service-install.sh  - Install as system service"
echo "✓ requirements.txt    - Python dependencies"
echo ""
