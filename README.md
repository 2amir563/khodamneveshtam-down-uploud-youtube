

📦 فایل‌های مورد نیاز در گیتهاب:
در ریپازیتوری خود این 3 فایل را آپلود کنید:

README.md - توضیحات

install.sh - اسکریپت نصب اصلی

bot.py - کد اصلی ربات

🚀 دستور نصب نهایی (فقط این یک دستور را در سرور اجرا کنید):
bash
```
bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)
```

✅ بعد از نصب:
1. تنظیم توکن ربات:
bash
```
nano ~/telegram-download-bot/.env
```
3. نصب سرویس auto-start (اگر به صورت خودکار نصب نشد):
bash
```
cd ~/telegram-download-bot
sudo ./service-install.sh
```
5. شروع سرویس:
bash
```
sudo systemctl start telegram-download-bot
```
7. بررسی وضعیت:
bash
```
sudo systemctl status telegram-download-bot
```
🔧 مدیریت ربات:
bash
# استفاده از منیجر (راحت‌تر)

```
cd ~/telegram-download-bot
./manager.sh
```

# یا دستورات مستقیم

```
sudo systemctl status telegram-download-bot
```
```
sudo journalctl -u telegram-download-bot -f
```
```
sudo systemctl restart telegram-download-bot
```
🎯 ویژگی‌های این نسخه:
نصب کامل با یک دستور

سرویس systemd خودکار - اجرا با روشن شدن سرور

ری‌استارت خودکار - اگر کرش کند

نمایش حجم فایل در کنار هر کیفیت

منیجر راحت برای مدیریت

لاگ‌گیری کامل - هم در فایل هم در systemd

حذف آسان با ./uninstall.sh

ربات شما حالا:

✅ با یک دستور نصب می‌شود

✅ با روشن شدن سرور اجرا می‌شود

✅ اگر کرش کند، ری‌استارت می‌شود

✅ مدیریت آسان دارد

✅ حجم فایل‌ها را نشان می‌دهد

......................................................................................................................
.................................................................................................................
..............................................................................................................
# Telegram Download Bot

A Telegram bot that downloads YouTube videos and direct links without saving files on disk.

## Features
- 📥 Download YouTube videos (with quality selection)
- 🔗 Download from any direct link (HTTP/HTTPS)
- 💾 No files saved on server (memory-only streaming)
- ⚡ Fast and efficient
- 🛠️ Easy installation and uninstallation

## Quick Installation (One Command)

```bash
bash <(curl -s https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/oneclick-install.sh)



برای اجرا کد زیر را در سرور بزنید

```
bash <(curl -s https://raw.githubusercontent.com/2amir563/khodamneveshtam-down-uploud-youtube/main/install.sh)
```

در اولین اجرا از شما BOT_TOKEN را می‌گیرد؛ وارد کنید و Enter بزنید.
در پایان، ربات به‌صورت سرویس systemd فعال و اتوماتیک در پس‌زمینه اجرا می‌شود.
برای بررسی وضعیت:

برای بررسی وضعیت:


```
sudo systemctl status khodamneveshtam-down-uploud-youtube
```

```
bash <2222222222222222222222222222gt-tunnel.sh)
```


