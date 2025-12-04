#!/bin/bash
# Start bot in background

cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ فایل .env یافت نشد!"
    echo "لطفاً ابتدا فایل .env.example را کپی و تنظیمات را وارد کنید:"
    echo "cp .env.example .env && nano .env"
    exit 1
fi

# Check if BOT_TOKEN is set
if ! grep -q "BOT_TOKEN=" .env || grep -q "BOT_TOKEN=123456789" .env; then
    echo "❌ TOKEN ربات تنظیم نشده است!"
    echo "لطفاً فایل .env را ویرایش کنید: nano .env"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start bot
echo "🤖 در حال راه‌اندازی ربات..."
python3 bot.py
