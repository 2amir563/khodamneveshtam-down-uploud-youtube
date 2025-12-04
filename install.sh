#!/bin/bash
# Auto Installer for YouTube & Direct Download Telegram Bot
# GitHub: https://github.com/2amir563/khodamneveshtam-down-uploud-youtube

set -e  # Exit on error

echo "🔧 شروع نصب ربات تلگرام..."

# Update system
echo "🔄 در حال بروزرسانی سیستم..."
sudo apt update -y
sudo apt upgrade -y

# Install dependencies
echo "📦 در حال نصب پیش‌نیازها..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Clone or update repository
if [ -d "khodamneveshtam-down-uploud-youtube" ]; then
    echo "📂 در حال بروزرسانی مخزن..."
    cd khodamneveshtam-down-uploud-youtube
    git pull
else
    echo "📥 در حال کلون کردن مخزن..."
    git clone https://github.com/2amir563/khodamneveshtam-down-uploud-youtube.git
    cd khodamneveshtam-down-uploud-youtube
fi

# Create virtual environment
echo "🐍 در حال ایجاد محیط مجازی..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📦 در حال نصب پکیج‌های پایتون..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup .env file
if [ ! -f ".env" ]; then
    echo "⚙️ ایجاد فایل .env..."
    cp .env.example .env
    echo "✏️ لطفاً TOKEN ربات را در فایل .env وارد کنید:"
    echo "BOT_TOKEN=توکن_ربات_شما"
    echo "OWNER_ID=آیدی_شما"
    echo ""
    echo "📝 برای ویرایش فایل .env دستور زیر را اجرا کنید:"
    echo "nano .env"
fi

# Make scripts executable
chmod +x bot.py install.sh uninstall.sh

echo ""
echo "✅ نصب کامل شد!"
echo ""
echo "📋 دستورات مدیریتی:"
echo "────────────────────"
echo "🚀 شروع ربات:          ./bot.py"
echo "🔧 اجرا در پس‌زمینه:    ./start.sh"
echo "🛑 توقف ربات:          ./stop.sh"
echo "🗑️ حذف کامل:           ./uninstall.sh"
echo "📝 ویرایش تنظیمات:     nano .env"
echo ""
echo "💡 نکته: ابتدا فایل .env را ویرایش و TOKEN ربات را وارد کنید."
