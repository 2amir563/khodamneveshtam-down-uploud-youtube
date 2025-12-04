#!/bin/bash
# Stop bot

echo "🛑 در حال توقف ربات..."
pkill -f "python3 bot.py" 2>/dev/null
echo "✅ ربات متوقف شد."
