cd ~
cat > install-2amir.sh << 'EOF'
#!/bin/bash
echo "Installing from 2amir563 GitHub..."
cd ~
rm -rf telegram-download-bot
mkdir telegram-download-bot
cd telegram-download-bot

# Download files
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/requirements.txt
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/.env.example
curl -s -O https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/bot.py

# Setup
cp .env.example .env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chmod +x bot.py

echo "✅ Done! Edit .env then run: source venv/bin/activate && python3 bot.py"
EOF

chmod +x install-2amir.sh
./install-2amir.sh
