#!/bin/bash
# Telegram Download Bot - Complete Installer with Auto-Service
# GitHub: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube
# Run: bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)

set -e

echo "=========================================="
echo "  Telegram Download Bot - Complete Install"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() { echo -e "${BLUE}[→]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check if already installed
print_step "Checking existing installation..."
if [ -d "$HOME/telegram-download-bot" ]; then
    print_error "Bot already installed at $HOME/telegram-download-bot"
    echo "To reinstall: rm -rf ~/telegram-download-bot"
    exit 1
fi

# Step 1: Update system and install dependencies
print_step "Updating system and installing dependencies..."
sudo apt update -y > /dev/null 2>&1
sudo apt install -y python3 python3-pip python3-venv git curl wget ffmpeg > /dev/null 2>&1

# Step 2: Create directory
print_step "Creating bot directory..."
cd ~
mkdir telegram-download-bot
cd telegram-download-bot

# Step 3: Download files from your GitHub
print_step "Downloading bot files from GitHub..."
curl -s -o requirements.txt https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/requirements.txt
curl -s -o .env.example https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/.env.example
curl -s -o bot.py https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/bot.py

# Step 4: Create .env from example
cp .env.example .env

# Step 5: Setup Python environment
print_step "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Step 6: Create helper scripts
print_step "Creating helper scripts..."

# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "================================="
echo "  Telegram Download Bot"
echo "================================="
echo ""

# Check .env file
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create .env file: cp .env.example .env"
    echo "Then edit it: nano .env"
    exit 1
fi

# Check if token is set
if grep -q "BOT_TOKEN=your_bot_token_here" .env || grep -q "BOT_TOKEN=123456789" .env; then
    echo "❌ ERROR: Please edit .env file!"
    echo "Add your bot token from @BotFather"
    echo "Command: nano .env"
    exit 1
fi

# Setup virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Setting up Python environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start bot
echo "🚀 Starting bot..."
python3 bot.py
EOF

# Create service-install.sh
cat > service-install.sh << 'EOF'
#!/bin/bash
# Install bot as systemd service (auto-start on reboot)

echo "================================="
echo "  Installing as System Service"
echo "================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERROR: Please run with sudo!"
    echo "Usage: sudo ./service-install.sh"
    exit 1
fi

BOT_DIR="$(pwd)"
BOT_USER="$(whoami)"

echo "📁 Bot directory: $BOT_DIR"
echo "👤 Running as user: $BOT_USER"
echo ""

# Check if bot files exist
if [ ! -f "$BOT_DIR/bot.py" ]; then
    echo "❌ ERROR: bot.py not found!"
    exit 1
fi

if [ ! -f "$BOT_DIR/.env" ]; then
    echo "⚠️ WARNING: .env file not found!"
    echo "Please create .env file before starting service"
fi

# Create service file
SERVICE_FILE="/etc/systemd/system/telegram-download-bot.service"

echo "Creating systemd service..."
cat > $SERVICE_FILE << SERVICE
[Unit]
Description=Telegram Download Bot (YouTube + Direct Links)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$BOT_DIR/venv/bin/python3 $BOT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-download-bot

[Install]
WantedBy=multi-user.target
SERVICE

# Enable service
systemctl daemon-reload
systemctl enable telegram-download-bot.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "📋 Management Commands:"
echo "  Start:    sudo systemctl start telegram-download-bot"
echo "  Stop:     sudo systemctl stop telegram-download-bot"
echo "  Status:   sudo systemctl status telegram-download-bot"
echo "  Restart:  sudo systemctl restart telegram-download-bot"
echo "  Logs:     sudo journalctl -u telegram-download-bot -f"
echo ""
echo "🚀 To start the service now:"
echo "  sudo systemctl start telegram-download-bot"
echo ""
echo "💡 The bot will auto-start on server reboot!"
EOF

# Create manager.sh
cat > manager.sh << 'EOF'
#!/bin/bash
# Bot Management Script

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE="telegram-download-bot"

show_menu() {
    clear
    echo "========================================"
    echo "  Telegram Bot Manager"
    echo "========================================"
    echo "1. 📱 Start Bot (manual)"
    echo "2. 🛑 Stop Bot (manual)"
    echo "3. ⚙️ Install Auto-Start Service"
    echo "4. ▶️ Start Service"
    echo "5. ⏸️ Stop Service"
    echo "6. 📊 Service Status"
    echo "7. 📝 View Live Logs"
    echo "8. 🔄 Restart Service"
    echo "9. 🔧 Check Bot Files"
    echo "10. 📥 Update Bot from GitHub"
    echo "0. ❌ Exit"
    echo "========================================"
}

check_status() {
    if systemctl is-active --quiet $SERVICE 2>/dev/null; then
        echo -e "Status: \033[0;32mService RUNNING\033[0m"
    else
        echo -e "Status: \033[0;31mService STOPPED\033[0m"
    fi
}

case $1 in
    status)
        sudo systemctl status $SERVICE --no-pager -l 2>/dev/null || echo "Service not installed"
        ;;
    logs)
        sudo journalctl -u $SERVICE -f
        ;;
    start)
        sudo systemctl start $SERVICE
        ;;
    stop)
        sudo systemctl stop $SERVICE
        ;;
    restart)
        sudo systemctl restart $SERVICE
        ;;
    *)
        while true; do
            show_menu
            check_status
            echo ""
            read -p "Select option [0-10]: " choice
            
            case $choice in
                1)
                    echo "Starting bot manually..."
                    cd "$BOT_DIR"
                    ./start.sh
                    ;;
                2)
                    echo "Stopping bot..."
                    pkill -f "python3 bot.py" 2>/dev/null
                    echo "Bot stopped"
                    sleep 2
                    ;;
                3)
                    echo "Installing auto-start service..."
                    sudo ./service-install.sh
                    ;;
                4)
                    echo "Starting service..."
                    sudo systemctl start $SERVICE 2>/dev/null
                    sleep 2
                    sudo systemctl status $SERVICE --no-pager -l 2>/dev/null || echo "Service not found"
                    ;;
                5)
                    echo "Stopping service..."
                    sudo systemctl stop $SERVICE 2>/dev/null
                    sleep 2
                    sudo systemctl status $SERVICE --no-pager -l 2>/dev/null || echo "Service not found"
                    ;;
                6)
                    sudo systemctl status $SERVICE --no-pager -l 2>/dev/null || echo "Service not installed"
                    ;;
                7)
                    echo "Showing live logs (Ctrl+C to exit)..."
                    sudo journalctl -u $SERVICE -f 2>/dev/null || echo "Service not installed"
                    ;;
                8)
                    echo "Restarting service..."
                    sudo systemctl restart $SERVICE 2>/dev/null
                    sleep 2
                    sudo systemctl status $SERVICE --no-pager -l 2>/dev/null || echo "Service not found"
                    ;;
                9)
                    echo "Checking bot files..."
                    cd "$BOT_DIR"
                    ls -la
                    echo ""
                    if [ -d "venv" ]; then
                        echo "Python version:"
                        venv/bin/python3 --version
                    fi
                    ;;
                10)
                    echo "Updating bot from GitHub..."
                    cd "$BOT_DIR"
                    git pull origin main 2>/dev/null || echo "Git not configured"
                    echo "Update complete. Restart service if needed."
                    ;;
                0)
                    echo "Goodbye! 👋"
                    exit 0
                    ;;
                *)
                    echo "Invalid option"
                    ;;
            esac
            
            echo ""
            read -p "Press Enter to continue..."
        done
        ;;
esac
EOF

# Create uninstall.sh
cat > uninstall.sh << 'EOF'
#!/bin/bash
# Uninstall script

echo "================================="
echo "  Uninstalling Telegram Bot"
echo "================================="
echo ""

# Stop bot
echo "Stopping bot..."
pkill -f "python3 bot.py" 2>/dev/null && echo "Bot stopped."

# Remove service if exists
if [ -f "/etc/systemd/system/telegram-download-bot.service" ]; then
    echo "Removing systemd service..."
    sudo systemctl stop telegram-download-bot.service 2>/dev/null
    sudo systemctl disable telegram-download-bot.service 2>/dev/null
    sudo rm -f /etc/systemd/system/telegram-download-bot.service
    sudo systemctl daemon-reload
    echo "Service removed."
fi

# Ask for directory removal
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
echo "✅ Uninstall complete!"
EOF

# Step 7: Make scripts executable
chmod +x bot.py start.sh service-install.sh manager.sh uninstall.sh

print_success "Installation complete!"
echo ""
echo "=========================================="
echo "📋 NEXT STEPS"
echo "=========================================="
echo ""
echo "1. 📝 Edit configuration file:"
echo "   nano ~/telegram-download-bot/.env"
echo ""
echo "2. 🔑 Add your bot token (get from @BotFather on Telegram):"
echo "   BOT_TOKEN=7123456789:AAHdG6v4p8TeH-8hJk9lM2nOp3QrS5tUvWx"
echo "   OWNER_ID=123456789"
echo ""
echo "3. 🚀 Start the bot (choose one):"
echo "   Option A - Manual start: ./start.sh"
echo "   Option B - Auto-start service: sudo ./service-install.sh"
echo ""
echo "4. ⚙️ After installing service, start it:"
echo "   sudo systemctl start telegram-download-bot"
echo ""
echo "=========================================="
echo "🔧 Management Commands"
echo "=========================================="
echo "Start manually:     ./start.sh"
echo "Install service:    sudo ./service-install.sh"
echo "Check status:       sudo systemctl status telegram-download-bot"
echo "View logs:          sudo journalctl -u telegram-download-bot -f"
echo "Use manager:        ./manager.sh"
echo "Uninstall:          ./uninstall.sh"
echo ""
echo "🚀 Bot will auto-start on server reboot!"
echo "=========================================="
