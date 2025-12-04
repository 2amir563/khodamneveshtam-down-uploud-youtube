#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Telegram Download/Upload Bot with YouTube Support
# Created by: 2ami-563

import os
import logging
import asyncio
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ChatAction
import yt_dlp
import re
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن بات خود را اینجا قرار دهید
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# محدودیت اندازه فایل (MB)
MAX_FILE_SIZE = 2000  # 2GB برای بات‌های معمولی

# حالت‌های مکالمه
SELECT_QUALITY, SELECT_FORMAT = range(2)

class YouTubeDownloader:
    """کلاس مدیریت دانلود از یوتیوب"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات ویدیو"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                formats = []
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        formats.append({
                            'format_id': f['format_id'],
                            'ext': f['ext'],
                            'resolution': f.get('resolution', 'N/A'),
                            'filesize': f.get('filesize', 0),
                            'quality': f.get('quality', 0),
                        })
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': formats,
                    'webpage_url': info.get('webpage_url', url),
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    async def download_video(self, url: str, format_id: str, quality: str) -> Optional[str]:
        """دانلود ویدیو با فرمت و کیفیت مشخص"""
        try:
            opts = {
                'format': f'{format_id}[height<={quality}]' if quality else format_id,
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
                'progress_hooks': [self.progress_hook],
            }
            
            os.makedirs('downloads', exist_ok=True)
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename
                
                # اگر فایل با پسوند متفاوت باشد
                for ext in ['mp4', 'webm', 'mkv', 'mp3']:
                    alt_filename = filename.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(alt_filename):
                        return alt_filename
            
            return None
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def progress_hook(self, d):
        """هوک پیشرفت دانلود"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A')
            logger.info(f"Downloading: {percent} at {speed}")

class TelegramBot:
    """کلاس اصلی بات تلگرام"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.youtube_dl = YouTubeDownloader()
        self.user_data = {}
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """تنظیم هندلرهای بات"""
        
        # هندلر دستور /start
        start_handler = CommandHandler('start', self.start_command)
        self.app.add_handler(start_handler)
        
        # هندلر دستور /help
        help_handler = CommandHandler('help', self.help_command)
        self.app.add_handler(help_handler)
        
        # هندلر دستور /download
        download_handler = CommandHandler('download', self.download_command)
        self.app.add_handler(download_handler)
        
        # هندلر برای لینک‌های یوتیوب
        youtube_handler = MessageHandler(
            filters.TEXT & filters.Regex(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'),
            self.handle_youtube_link
        )
        self.app.add_handler(youtube_handler)
        
        # هندلر برای فایل‌های آپلود شده
        file_handler = MessageHandler(filters.VIDEO | filters.AUDIO | filters.Document.ALL, self.handle_file)
        self.app.add_handler(file_handler)
        
        # هندلر برای متن
        text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        self.app.add_handler(text_handler)
        
        # هندلر خطا
        self.app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        welcome_text = f"""
سلام {user.first_name}!
به ربات دانلود/آپلود خوش آمدید.

🔹 **قابلیت‌ها:**
• دانلود از یوتیوب
• آپلود فایل به تلگرام
• تبدیل فرمت‌های مختلف

📌 **دستورات:**
/start - شروع ربات
/help - راهنمایی
/download [لینک] - دانلود از یوتیوب

📎 **روش استفاده:**
1. لینک یوتیوب را بفرستید
2. کیفیت مورد نظر را انتخاب کنید
3. فایل دانلود شده برای شما ارسال می‌شود

⚠️ **توجه:** حداکثر سایز فایل: {MAX_FILE_SIZE}MB
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = """
📖 **راهنمای ربات:**

🔹 **برای دانلود از یوتیوب:**
1. لینک ویدیو را برای ربات بفرستید
2. کیفیت مورد نظر را انتخاب کنید
3. منتظر دانلود و ارسال فایل بمانید

🔹 **برای آپلود فایل:**
فایل (ویدیو، صدا، سند) را مستقیماً برای ربات بفرستید

🔹 **فرمت‌های پشتیبانی شده:**
• ویدیو: MP4, MKV, WEBM, AVI
• صدا: MP3, M4A, WAV, OGG
• سند: PDF, TXT, DOC, ZIP

⚠️ **محدودیت‌ها:**
• حداکثر حجم فایل: 2GB
• مدت زمان ویدیو: حداکثر 4 ساعت

🛠 **پشتیبانی:** @your_support_channel
        """
        await update.message.reply_text(help_text)
    
    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /download"""
        if not context.args:
            await update.message.reply_text("⚠️ لطفاً لینک یوتیوب را بعد از دستور وارد کنید.\nمثال: /download https://youtube.com/watch?v=...")
            return
        
        url = context.args[0]
        await self.process_youtube_url(update, context, url)
    
    async def handle_youtube_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش لینک یوتیوب ارسالی"""
        url = update.message.text
        await self.process_youtube_url(update, context, url)
    
    async def process_youtube_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        """پردازش URL یوتیوب"""
        await update.message.reply_text("🔍 در حال دریافت اطلاعات ویدیو...")
        
        # ارسال وضعیت تایپینگ
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )
        
        # دریافت اطلاعات ویدیو
        video_info = self.youtube_dl.get_video_info(url)
        
        if not video_info:
            await update.message.reply_text("❌ خطا در دریافت اطلاعات ویدیو. لطفاً لینک را بررسی کنید.")
            return
        
        # ذخیره اطلاعات برای کاربر
        user_id = update.effective_user.id
        self.user_data[user_id] = {
            'youtube_url': url,
            'video_info': video_info,
            'last_interaction': datetime.now()
        }
        
        # نمایش اطلاعات ویدیو و گزینه‌های کیفیت
        title = video_info['title'][:100] + "..." if len(video_info['title']) > 100 else video_info['title']
        duration = video_info['duration']
        
        # محاسبه مدت زمان
        if duration > 0:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
        else:
            duration_str = "نامشخص"
        
        # ایجاد گزینه‌های کیفیت
        formats = video_info['formats'][:10]  # حداکثر 10 فرمت
        
        if not formats:
            await update.message.reply_text("❌ هیچ فرمت مناسبی برای این ویدیو یافت نشد.")
            return
        
        # ساخت کیبورد برای انتخاب کیفیت
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = []
        for fmt in formats:
            quality = fmt.get('resolution', 'N/A')
            ext = fmt.get('ext', 'mp4').upper()
            size = fmt.get('filesize', 0)
            
            if size > 0:
                size_mb = size / (1024 * 1024)
                size_str = f"{size_mb:.1f}MB"
            else:
                size_str = "نامشخص"
            
            btn_text = f"{quality} ({ext}) - {size_str}"
            callback_data = f"format_{fmt['format_id']}_{quality.split('x')[1] if 'x' in quality else '720'}"
            
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        
        # اضافه کردن دکمه کنسل
        keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        info_text = f"""
🎬 **{title}**

⏱ مدت زمان: {duration_str}

📊 **لطفاً کیفیت مورد نظر را انتخاب کنید:**
        """
        
        await update.message.reply_text(info_text, reply_markup=reply_markup)
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش فایل آپلود شده"""
        try:
            file = None
            
            if update.message.video:
                file = update.message.video
            elif update.message.audio:
                file = update.message.audio
            elif update.message.document:
                file = update.message.document
            elif update.message.voice:
                file = update.message.voice
            
            if not file:
                await update.message.reply_text("❌ نوع فایل شناسایی نشد.")
                return
            
            # دریافت اطلاعات فایل
            file_size = file.file_size or 0
            file_name = file.file_name or "unknown"
            
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                await update.message.reply_text(f"⚠️ حجم فایل ({file_size/(1024*1024):.1f}MB) از حد مجاز ({MAX_FILE_SIZE}MB) بیشتر است.")
                return
            
            await update.message.reply_text(f"""
📁 **فایل دریافت شد:**

📛 نام: {file_name}
📦 حجم: {file_size/(1024*1024):.1f}MB
✅ فایل با موفقیت دریافت شد.

📤 در صورت نیاز می‌توانید فایل را برای دیگران فوروارد کنید.
            """)
            
        except Exception as e:
            logger.error(f"Error handling file: {e}")
            await update.message.reply_text("❌ خطا در پردازش فایل.")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش متن"""
        text = update.message.text
        
        if text.startswith('http'):
            await update.message.reply_text("🔗 لینک دریافت شد. اگر لینک یوتیوب است، به زودی پردازش می‌شود.")
        else:
            await update.message.reply_text(f"📝 متن شما: {text}\n\nبرای دانلود، لینک یوتیوب را ارسال کنید.")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ خطایی رخ داده است. لطفاً دوباره تلاش کنید."
                )
        except:
            pass
    
    def run(self):
        """اجرای بات"""
        logger.info("🤖 ربات در حال راه‌اندازی...")
        
        # اجرای بات
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        
        logger.info("🛑 ربات متوقف شد.")

# تابع اصلی
def main():
    """تابع اصلی اجرای برنامه"""
    
    print("""
    ====================================
      Telegram Download/Upload Bot
           با پشتیبانی یوتیوب
    ====================================
    
    ✨ در حال راه‌اندازی ربات...
    
    📌 نکات:
    1. توکن بات را در فایل تنظیم کنید
    2. از پایداری اینترنت اطمینان حاصل کنید
    3. برای توقف، Ctrl+C بزنید
    
    """)
    
    # بررسی وجود توکن
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ لطفاً ابتدا توکن بات را در متغیر BOT_TOKEN قرار دهید.")
        print("📝 راهنما: به @BotFather در تلگرام مراجعه کنید و بات جدید بسازید.")
        return
    
    # ایجاد دایرکتوری دانلود
    os.makedirs('downloads', exist_ok=True)
    
    # ایجاد و اجرای بات
    bot = TelegramBot(BOT_TOKEN)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\n🛑 ربات به درخواست کاربر متوقف شد.")
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")

if __name__ == "__main__":
    main()
