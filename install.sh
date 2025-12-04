#!/bin/bash
# One-line install on Ubuntu/Debian
sudo apt update && sudo apt install python3-pip git -y
git clone https://github.com/2amir563/khodamneveshtam-down-uploud-youtube.git
cd khodamneveshtam-down-uploud-youtube
pip3 install -r requirements.txt
cp .env.example .env
nano .env              # BOT_TOKEN را وارد کنید
chmod +x install.sh bot.py
# تست
python3 bot.py
