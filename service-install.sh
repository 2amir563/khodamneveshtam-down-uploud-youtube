#!/bin/bash
# Install as systemd service

cd "$(dirname "$0")"

SERVICE_FILE="khodamneveshtam-bot.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE"

echo "🔧 نصب به عنوان سرویس systemd..."

# Create service file
cat > /tmp/$SERVICE_FILE << EOL
[Unit]
Description=Khodamneveshtam YouTube & Direct Download Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=khodamneveshtam-bot

# Security
NoNewPrivileges=true
ProtectSystem=strict
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOL

# Copy service file
sudo cp /tmp/$SERVICE_FILE $SERVICE_PATH
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_FILE

echo ""
echo "✅ سرویس نصب شد!"
echo ""
echo "📋 دستورات مدیریت سرویس:"
echo "────────────────────────"
echo "🚀 شروع سرویس:     sudo systemctl start khodamneveshtam-bot"
echo "🔍 وضعیت سرویس:    sudo systemctl status khodamneveshtam-bot"
echo "📝 مشاهده لاگ‌ها:  sudo journalctl -u khodamneveshtam-bot -f"
echo "🛑 توقف سرویس:     sudo systemctl stop khodamneveshtam-bot"
echo "🔄 راه‌اندازی مجدد: sudo systemctl restart khodamneveshtam-bot"
echo ""
echo "💡 برای شروع سرویس: sudo systemctl start khodamneveshtam-bot"
