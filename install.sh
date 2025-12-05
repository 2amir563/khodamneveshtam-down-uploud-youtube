#!/bin/bash
# Simple Telegram Download Bot Installer - NO FFMPEG REQUIRED
# Run: bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)

echo "=========================================="
echo "  Simple Telegram Download Bot Installer"
echo "  NO FFMPEG REQUIRED"
echo "  GitHub: 2amir563/khodamneveshtam-down-uploud-youtube"
echo "=========================================="
echo ""

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_info() { echo -e "${BLUE}[→]${NC} $1"; }

# Check if bot exists
if [ -d "$HOME/telegram-download-bot" ]; then
    print_info "Bot directory exists, updating..."
    cd ~/telegram-download-bot
    ./stop.sh 2>/dev/null || true
else
    print_info "Creating bot directory..."
    mkdir -p ~/telegram-download-bot
    cd ~/telegram-download-bot
fi

# Update system
print_info "Updating system..."
sudo apt update -y > /dev/null 2>&1

# Install basic dependencies (NO FFMPEG)
print_info "Installing Python and basic tools..."
sudo apt install -y python3 python3-pip python3-venv curl wget git > /dev/null 2>&1

# Download files
print_info "Downloading files..."

files=(
    "bot.py"
    "requirements.txt"
    ".env.example"
)

for file in "${files[@]}"; do
    print_info "Downloading $file..."
    curl -s -O "https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/$file" || {
        print_error "Failed to download $file"
        exit 1
    }
done

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success ".env file created"
fi

# Create helper scripts
print_info "Creating helper scripts..."

# start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "================================="
echo "  Simple Download Bot"
echo "  No ffmpeg required"
echo "================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Run: cp .env.example .env"
    echo "Then edit: nano .env"
    exit 1
fi

# Check token
if grep -q "BOT_TOKEN=your_bot_token" .env; then
    echo "❌ Please edit .env file!"
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
else
    source venv/bin/activate
fi

echo ""
echo "Starting bot..."
echo "Press Ctrl+C to stop"
echo ""
python3 bot.py
EOF

# stop.sh
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping bot..."
pkill -f "python3 bot.py" 2>/dev/null && echo "Bot stopped" || echo "Bot was not running"
EOF

# update.sh
cat > update.sh << 'EOF'
#!/bin/bash
echo "Updating bot..."
cd "$(dirname "$0")"
./stop.sh

echo "Downloading updates..."
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/bot.py
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/requirements.txt

source venv/bin/activate
pip install -r requirements.txt --upgrade

echo "✅ Update complete!"
echo "Start bot: ./start.sh"
EOF

# uninstall.sh
cat > uninstall.sh << 'EOF'
#!/bin/bash
echo "Uninstalling bot..."
cd "$(dirname "$0")"
./stop.sh

read -p "Remove bot directory? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ~
    rm -rf telegram-download-bot
    echo "✅ Bot removed"
else
    echo "✅ Bot stopped but directory kept"
fi
EOF

# Setup Python environment
print_info "Setting up Python..."
python3 -m venv venv 2>/dev/null || {
    print_info "Creating virtual environment..."
    python3 -m pip install virtualenv
    virtualenv venv
}

source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Make scripts executable
chmod +x *.sh bot.py

print_success "✅ Installation complete!"
echo ""
echo "=========================================="
echo "🚀 NEXT STEPS"
echo "=========================================="
echo ""
echo "1. Edit configuration:"
echo "   nano ~/telegram-download-bot/.env"
echo ""
echo "2. Add your bot token from @BotFather:"
echo "   BOT_TOKEN=7123456789:AAHdG6v4p8TeH-8hJk9lM2nOp3QrS5tUvWx"
echo ""
echo "3. Start the bot:"
echo "   cd ~/telegram-download-bot"
echo "   ./start.sh"
echo ""
echo "=========================================="
echo "🔧 Commands:"
echo "=========================================="
echo "Start:      ./start.sh"
echo "Stop:       ./stop.sh"
echo "Update:     ./update.sh"
echo "Uninstall:  ./uninstall.sh"
echo ""
echo "✅ No ffmpeg required!"
echo "✅ Works on all systems"
