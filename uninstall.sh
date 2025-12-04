#!/bin/bash
# Uninstall bot completely

cd "$(dirname "$0")"

echo "🗑️ در حال حذف ربات..."
echo ""

# Stop bot first
pkill -f "python3 bot.py" 2>/dev/null

# Remove service if exists
if [ -f "/etc/systemd/system/khodamneveshtam-bot.service" ]; then
    echo "🛑 توقف سرویس..."
    sudo systemctl stop khodamneveshtam-bot.service
    sudo systemctl disable khodamneveshtam-bot.service
    sudo rm -f /etc/systemd/system/khodamneveshtam-bot.service
    sudo systemctl daemon-reload
fi

# Go to parent directory
cd ..

# Ask for confirmation
read -p "آیا مطمئن هستید که می‌خواهید ربات را حذف کنید؟ (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 در حال پاکسازی فایل‌ها..."
    rm -rf khodamneveshtam-down-uploud-youtube
    
    echo ""
    echo "✅ ربات با موفقیت حذف شد!"
    echo ""
    echo "💡 نکته: پکیج‌های پایتون همچنان در سیستم باقی مانده‌اند."
    echo "اگر می‌خواهید آن‌ها را نیز حذف کنید، دستور زیر را اجرا کنید:"
    echo "pip3 uninstall python-telegram-bot yt-dlp python-dotenv aiohttp"
else
    echo "❌ عملیات لغو شد."
fi
