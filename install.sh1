#!/bin/bash
# Telegram Download Bot Installer for 2amir563
# Run: bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)

echo "=========================================="
echo "  Telegram Download Bot Installer"
echo "  GitHub: 2amir563/khodamneveshtam-down-uploud-youtube"
echo "=========================================="
echo ""

# Exit on error
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

# Step 1: Check system
print_info "Checking system..."
if [ -d "$HOME/telegram-download-bot" ]; then
    print_error "Bot already exists at $HOME/telegram-download-bot"
    echo "Remove it first: rm -rf ~/telegram-download-bot"
    exit 1
fi

# Step 2: Update system
print_info "Updating packages..."
sudo apt update -y > /dev/null 2>&1

# Step 3: Install dependencies
print_info "Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv git curl wget ffmpeg > /dev/null 2>&1

# Step 4: Create directory
print_info "Creating bot directory..."
cd ~
mkdir telegram-download-bot
cd telegram-download-bot

# Step 5: Download files from your GitHub
print_info "Downloading files from GitHub..."

# Download requirements.txt
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/requirements.txt

# Download bot.py
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/bot.py

# Download .env.example
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/.env.example

# Create .env from example
cp .env.example .env

# Step 6: Create helper scripts
print_info "Creating helper scripts..."

# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "================================="
echo "  Starting Telegram Download Bot"
echo "================================="
echo ""

# Check .env
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Run: cp .env.example .env"
    echo "Then edit: nano .env"
    exit 1
fi

# Check if token is set
if grep -q "BOT_TOKEN=123456789" .env || grep -q "BOT_TOKEN=your_bot_token" .env; then
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
else
    source venv/bin/activate
fi

# Start bot
echo "Starting bot..."
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
echo "================================="
echo "  Uninstalling Telegram Bot"
echo "================================="
echo ""

# Stop bot
echo "Stopping bot..."
pkill -f "python3 bot.py" 2>/dev/null && echo "Bot stopped."

# Remove systemd service if exists
if [ -f "/etc/systemd/system/telegram-download-bot.service" ]; then
    echo "Removing systemd service..."
    sudo systemctl stop telegram-download-bot.service
    sudo systemctl disable telegram-download-bot.service
    sudo rm -f /etc/systemd/system/telegram-download-bot.service
    sudo systemctl daemon-reload
    echo "Service removed."
fi

# Ask about directory removal
read -p "Remove bot directory? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing directory..."
    cd ~
    rm -rf telegram-download-bot
    echo "Directory removed."
else
    echo "Directory kept at ~/telegram-download-bot"
fi

echo ""
echo "Uninstall complete!"
echo "Note: Python packages may still be installed."
EOF

# Create service-install.sh
cat > service-install.sh << 'EOF'
#!/bin/bash
echo "================================="
echo "  Installing as System Service"
echo "================================="
echo ""

cd "$(dirname "$0")"

# Check if root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "sudo ./service-install.sh"
    exit 1
fi

# Create service file
SERVICE_FILE="/etc/systemd/system/telegram-download-bot.service"

cat > $SERVICE_FILE << SERVICE
[Unit]
Description=Telegram Download Bot
After=network.target

[Service]
Type=simple
User=$(logname)
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

# Enable service
systemctl daemon-reload
systemctl enable telegram-download-bot.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "📋 Commands:"
echo "  Start:  sudo systemctl start telegram-download-bot"
echo "  Stop:   sudo systemctl stop telegram-download-bot"
echo "  Status: sudo systemctl status telegram-download-bot"
echo "  Logs:   sudo journalctl -u telegram-download-bot -f"
echo ""
echo "To start: sudo systemctl start telegram-download-bot"
EOF

# Step 7: Setup Python environment
print_info "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Make scripts executable
chmod +x bot.py start.sh stop.sh uninstall.sh service-install.sh

print_success "Installation complete!"
echo ""
echo "=========================================="
echo "📋 NEXT STEPS"
echo "=========================================="
echo ""
echo "1. Edit configuration file:"
echo "   nano ~/telegram-download-bot/.env"
echo ""
echo "2. Add your bot token (from @BotFather):"
echo "   BOT_TOKEN=7123456789:AAHdG6v4p8TeH-8hJk9lM2nOp3QrS5tUvWx"
echo ""
echo "3. Start the bot:"
echo "   cd ~/telegram-download-bot"
echo "   ./start.sh"
echo ""
echo "4. Optional - Run as service (auto-start):"
echo "   sudo ./service-install.sh"
echo "   sudo systemctl start telegram-download-bot"
echo ""
echo "=========================================="
echo "🔧 Management Commands"
echo "=========================================="
echo "Start:        ./start.sh"
echo "Stop:         ./stop.sh"
echo "Uninstall:    ./uninstall.sh"
echo "Install service: sudo ./service-install.sh"
echo ""
echo "Press Ctrl+C to stop the bot"
