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
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Step 1: Check system
print_info "Checking system..."
if [ -d "$HOME/telegram-download-bot" ]; then
    print_warning "Bot directory already exists at $HOME/telegram-download-bot"
    read -p "Do you want to remove and reinstall? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing installation..."
        rm -rf ~/telegram-download-bot
    else
        print_info "You can update manually by running:"
        echo "cd ~/telegram-download-bot && git pull"
        exit 0
    fi
fi

# Step 2: Update system
print_info "Updating system packages..."
sudo apt update -y > /dev/null 2>&1
sudo apt upgrade -y > /dev/null 2>&1

# Step 3: Install essential dependencies
print_info "Installing essential dependencies..."
sudo apt install -y python3 python3-pip python3-venv git curl wget > /dev/null 2>&1

# Step 4: Install ffmpeg (CRITICAL for YouTube downloads)
print_info "Installing ffmpeg for video processing..."
if command -v ffmpeg &> /dev/null; then
    print_success "ffmpeg is already installed"
else
    # Try to install ffmpeg
    if sudo apt install -y ffmpeg > /dev/null 2>&1; then
        print_success "ffmpeg installed successfully"
    else
        print_warning "Standard ffmpeg installation failed, trying alternative method..."
        
        # Add ffmpeg repository for older systems
        sudo add-apt-repository -y ppa:jonathonf/ffmpeg-4 2>/dev/null || true
        sudo apt update -y > /dev/null 2>&1
        
        if sudo apt install -y ffmpeg > /dev/null 2>&1; then
            print_success "ffmpeg installed via PPA"
        else
            print_error "Failed to install ffmpeg automatically"
            print_info "Please install ffmpeg manually:"
            echo "sudo apt install -y ffmpeg"
            print_info "Or visit: https://ffmpeg.org/download.html"
            exit 1
        fi
    fi
fi

# Verify ffmpeg installation
if ! command -v ffmpeg &> /dev/null; then
    print_error "ffmpeg is not installed. YouTube downloads will not work!"
    print_info "You can try installing manually:"
    echo "wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    echo "tar -xf ffmpeg-release-amd64-static.tar.xz"
    echo "sudo mv ffmpeg-*-static/ffmpeg /usr/local/bin/"
    echo "sudo mv ffmpeg-*-static/ffprobe /usr/local/bin/"
else
    ffmpeg_version=$(ffmpeg -version | head -n1 | awk '{print $3}')
    print_success "ffmpeg version $ffmpeg_version installed"
fi

# Step 5: Create directory
print_info "Creating bot directory..."
mkdir -p ~/telegram-download-bot
cd ~/telegram-download-bot

# Step 6: Download files from your GitHub
print_info "Downloading files from GitHub..."

# List of required files
files=(
    "requirements.txt"
    "bot.py"
    ".env.example"
)

for file in "${files[@]}"; do
    print_info "Downloading $file..."
    curl -s -O "https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/$file" || {
        print_error "Failed to download $file"
        exit 1
    }
done

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success ".env file created from example"
else
    print_info ".env file already exists (keeping your settings)"
fi

# Step 7: Create helper scripts
print_info "Creating helper scripts..."

# Create start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "================================="
echo "  Starting Telegram Download Bot"
echo "================================="
echo ""

# Check system dependencies
echo "Checking system dependencies..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ERROR: ffmpeg is not installed!"
    echo "YouTube downloads will not work without ffmpeg."
    echo "Install it with: sudo apt install ffmpeg"
    echo "Or run the installer again: ./install.sh"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python3 is not installed!"
    exit 1
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Run: cp .env.example .env"
    echo "Then edit: nano .env"
    exit 1
fi

# Check if token is set
if grep -q "BOT_TOKEN=123456789" .env || grep -q "BOT_TOKEN=your_bot_token" .env; then
    echo "❌ ERROR: Please edit .env file!"
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
    echo "✅ Python environment created"
else
    source venv/bin/activate
fi

# Check Python packages
echo "Checking Python packages..."
if ! python3 -c "import telebot, yt_dlp, dotenv" 2>/dev/null; then
    echo "Installing missing packages..."
    pip install -r requirements.txt
fi

# Display system info
echo ""
echo "📊 System Information:"
echo "Python: $(python3 --version | cut -d' ' -f2)"
echo "ffmpeg: $(ffmpeg -version 2>/dev/null | head -n1 | awk '{print $3}')"
echo "Bot directory: $(pwd)"
echo ""

# Start bot
echo "Starting bot..."
echo "Press Ctrl+C to stop the bot"
echo ""
python3 bot.py
EOF

# Create stop.sh
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping bot..."
if pkill -f "python3 bot.py" 2>/dev/null; then
    echo "✅ Bot stopped successfully"
else
    echo "ℹ️ Bot was not running"
fi
EOF

# Create update.sh
cat > update.sh << 'EOF'
#!/bin/bash
echo "================================="
echo "  Updating Telegram Bot"
echo "================================="
echo ""

cd "$(dirname "$0")"

# Stop bot if running
echo "Stopping bot..."
pkill -f "python3 bot.py" 2>/dev/null && echo "Bot stopped."

# Backup .env file
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "Backup of .env created"
fi

# Download updated files
echo "Downloading updates..."
files=(
    "requirements.txt"
    "bot.py"
    ".env.example"
    "install.sh"
)

for file in "${files[@]}"; do
    echo "Updating $file..."
    curl -s -O "https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/$file" || {
        echo "❌ Failed to download $file"
    }
done

# Restore .env if it was overwritten
if [ -f ".env.backup" ] && [ ! -s ".env" ]; then
    mv .env.backup .env
    echo "Restored .env from backup"
fi

# Update Python packages
echo "Updating Python packages..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt --upgrade
    echo "✅ Packages updated"
fi

# Make scripts executable
chmod +x *.sh bot.py

echo ""
echo "✅ Update complete!"
echo "You can start the bot with: ./start.sh"
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
if pkill -f "python3 bot.py" 2>/dev/null; then
    echo "✅ Bot stopped"
fi

# Remove systemd service if exists
if [ -f "/etc/systemd/system/telegram-download-bot.service" ]; then
    echo "Removing systemd service..."
    sudo systemctl stop telegram-download-bot.service 2>/dev/null
    sudo systemctl disable telegram-download-bot.service 2>/dev/null
    sudo rm -f /etc/systemd/system/telegram-download-bot.service
    sudo systemctl daemon-reload
    echo "✅ Service removed"
fi

# Ask about directory removal
read -p "Remove bot directory? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing directory..."
    cd ~
    if rm -rf telegram-download-bot; then
        echo "✅ Directory removed"
    else
        echo "❌ Failed to remove directory"
    fi
else
    echo "ℹ️ Directory kept at ~/telegram-download-bot"
    echo "You can start it again with: cd ~/telegram-download-bot && ./start.sh"
fi

echo ""
echo "================================="
echo "📝 Note:"
echo "================================="
echo "1. ffmpeg is still installed on your system"
echo "2. Python packages in venv were removed with directory"
echo "3. To completely remove, delete the directory manually"
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
    echo "❌ Please run with sudo:"
    echo "sudo ./service-install.sh"
    exit 1
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed!"
    echo "YouTube downloads will not work without ffmpeg."
    echo "Install it first: sudo apt install ffmpeg"
    exit 1
fi

# Create service file
SERVICE_FILE="/etc/systemd/system/telegram-download-bot.service"
USER_HOME=$(eval echo ~$(logname))
BOT_DIR="$USER_HOME/telegram-download-bot"

if [ ! -d "$BOT_DIR" ]; then
    echo "❌ Bot directory not found: $BOT_DIR"
    echo "Run the installer first: ./install.sh"
    exit 1
fi

cat > $SERVICE_FILE << SERVICE
[Unit]
Description=Telegram Download Bot
After=network.target
Requires=network.target

[Service]
Type=simple
User=$(logname)
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$BOT_DIR/venv/bin/python3 $BOT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-download-bot

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$BOT_DIR
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICE

# Enable service
systemctl daemon-reload
systemctl enable telegram-download-bot.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "================================="
echo "📋 Management Commands:"
echo "================================="
echo "Start:  sudo systemctl start telegram-download-bot"
echo "Stop:   sudo systemctl stop telegram-download-bot"
echo "Status: sudo systemctl status telegram-download-bot"
echo "Logs:   sudo journalctl -u telegram-download-bot -f"
echo "Enable auto-start: sudo systemctl enable telegram-download-bot"
echo ""
echo "================================="
echo "🚀 Quick Start:"
echo "================================="
echo "1. Start the service:"
echo "   sudo systemctl start telegram-download-bot"
echo ""
echo "2. Check status:"
echo "   sudo systemctl status telegram-download-bot"
echo ""
echo "3. View logs:"
echo "   sudo journalctl -u telegram-download-bot -f"
EOF

# Create install.sh (local copy)
cat > install.sh << 'EOF'
#!/bin/bash
echo "⚠️  This is a local copy of install.sh"
echo "For fresh installation, use the online version:"
echo "bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)"
echo ""
echo "To update, run: ./update.sh"
EOF

# Step 8: Setup Python environment
print_info "Setting up Python environment..."
if ! python3 -m venv venv 2>/dev/null; then
    print_error "Failed to create virtual environment"
    print_info "Trying alternative method..."
    python3 -m pip install virtualenv 2>/dev/null || true
    virtualenv venv || {
        print_error "Could not create virtual environment"
        print_info "Continuing with system Python..."
    }
fi

if [ -d "venv" ]; then
    source venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    print_info "Installing Python packages..."
    pip install -r requirements.txt > /dev/null 2>&1
    print_success "Python packages installed"
else
    print_warning "Using system Python (not recommended)"
    pip3 install --upgrade pip > /dev/null 2>&1
    pip3 install -r requirements.txt > /dev/null 2>&1
fi

# Make scripts executable
chmod +x start.sh stop.sh update.sh uninstall.sh service-install.sh install.sh bot.py

print_success "✅ Installation complete!"
echo ""
echo "=========================================="
echo "🚀 NEXT STEPS"
echo "=========================================="
echo ""
echo "1. 📝 Edit configuration file:"
echo "   nano ~/telegram-download-bot/.env"
echo ""
echo "2. 🔑 Add your bot token (from @BotFather):"
echo "   BOT_TOKEN=7123456789:AAHdG6v4p8TeH-8hJk9lM2nOp3QrS5tUvWx"
echo ""
echo "3. ▶️  Start the bot:"
echo "   cd ~/telegram-download-bot"
echo "   ./start.sh"
echo ""
echo "4. ⚙️  Optional - Run as service (auto-start):"
echo "   sudo ./service-install.sh"
echo "   sudo systemctl start telegram-download-bot"
echo ""
echo "=========================================="
echo "🔧 MANAGEMENT COMMANDS"
echo "=========================================="
echo "Start:        ./start.sh"
echo "Stop:         ./stop.sh"
echo "Update:       ./update.sh"
echo "Uninstall:    ./uninstall.sh"
echo "Install service: sudo ./service-install.sh"
echo ""
echo "=========================================="
echo "📊 SYSTEM CHECK"
echo "=========================================="
echo "Python: $(python3 --version 2>/dev/null || echo 'Not found')"
echo "ffmpeg: $(command -v ffmpeg 2>/dev/null && ffmpeg -version 2>/dev/null | head -n1 | awk '{print $3}' || echo 'Not found')"
echo "Bot directory: $(pwd)"
echo ""
echo "=========================================="
echo "⚠️  IMPORTANT NOTES"
echo "=========================================="
echo "1. ffmpeg is REQUIRED for YouTube downloads"
echo "2. Max file size: 2GB"
echo "3. Files are not stored on server"
echo "4. Bot shows file size before downloading"
echo ""
echo "Press Ctrl+C to stop the bot when running"
echo "Telegram: @BotFather to get token"
