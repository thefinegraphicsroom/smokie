import os
from pathlib import Path
import yt_dlp
from pyrogram import Client, filters, enums  # Added enums import
import re
import logging
import asyncio
import math
import time  # Added missing time import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
API_ID = "26490815"  # Replace with your actual API ID
API_HASH = "b99d8504b8812f9ec395ec61c010ac32"  # Replace with your actual API Hash
BOT_TOKEN = "7060430437:AAH6NkmJ17Q09fXf6dPzM2ykmo7b8xDW5TQ"  # Replace with your bot token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory of main.py
YT_COOKIES_PATH = os.path.join(BASE_DIR, "cookies.txt")  # cookies.txt in the same folder

# Initialize the Pyrogram client
bot = Client(
    "youtube_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,  # Number of workers to handle simultaneous user requests
    parse_mode=enums.ParseMode.MARKDOWN  # Fixed ParseMode reference
)

class YouTubeDownloader:
    def __init__(self, cookies_path=None):
        self.cookies_path = cookies_path

    def _sanitize_filename(self, title):
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = title.replace(' ', '_')
        title = title[:50]
        return f"{title}_{int(time.time())}"

    def _get_ydl_opts(self, output_filename, progress_hook=None):
        opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'outtmpl': output_filename,
            'cookiefile': YT_COOKIES_PATH,  # Always use the predefined path
            'no_warnings': True,
            'noprogress': False,  # Disable 'noprogress' to enable progress output
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }

        # Attach progress hook if provided
        if progress_hook:
            opts['progress_hooks'] = [progress_hook]

        return opts

    def progress_hook(status):
        if status['status'] == 'downloading':
            downloaded = status.get('downloaded_bytes', 0)
            total = status.get('total_bytes', 0)
            if total > 0:
                progress_percent = downloaded / total * 100
                print(f"Download progress: {progress_percent:.2f}%")
            else:
                print("Downloading...")
        elif status['status'] == 'finished':
            print("Download complete. Now post-processing...")


    def validate_url(self, url):
        return url.startswith(('https://www.youtube.com/', 
                             'https://youtube.com/',
                             'https://youtu.be/'))

    def get_video_info(self, url):
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'filesize': info.get('filesize', 0)
                }
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None

    def format_size(self, size_bytes):
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def format_duration(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    async def download_video(self, url, chat_id):
        if not self.validate_url(url):
            return None, "Invalid YouTube URL"

        try:
            info = self.get_video_info(url)
            if not info:
                return None, "Could not fetch video information"

            safe_title = self._sanitize_filename(info['title'])
            output_path = f"downloads/{safe_title}.mp4"
            os.makedirs("downloads", exist_ok=True)

            # Define the progress hook for user updates
            def progress_hook(status):
                if status['status'] == 'downloading':
                    downloaded = status.get('downloaded_bytes', 0)
                    total = status.get('total_bytes', 0)
                    if total > 0:
                        progress_percent = downloaded / total * 100
                        print(f"Downloading: {progress_percent:.2f}%")
                elif status['status'] == 'finished':
                    print("Download complete. Now post-processing...")

            # Pass the progress hook to yt-dlp options
            ydl_opts = self._get_ydl_opts(output_path, progress_hook)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not os.path.exists(output_path):
                return None, "Download failed: File not created"

            file_size = os.path.getsize(output_path)
            if file_size > 2_000_000_000:
                os.remove(output_path)
                return None, "Video file exceeds Telegram's 2GB limit."

            return output_path, None

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download error for chat {chat_id}: {str(e)}")
            return None, "Download failed: Video unavailable or restricted"
        except Exception as e:
            logger.error(f"Unexpected error for chat {chat_id}: {str(e)}")
            return None, f"An unexpected error occurred: {str(e)}"

# Initialize downloader
downloader = YouTubeDownloader()

@bot.on_message(filters.command("start"))  # Changed app to bot
async def send_welcome(client, message):
    welcome_text = (
        "👋 Welcome to YouTube Video Downloader Bot!\n\n"
        "Simply send me a YouTube video link, and I'll download it in the best quality for you.\n\n"
        "Example link formats:\n"
        "▫️ https://www.youtube.com/watch?v=...\n"
        "▫️ https://youtu.be/..."
    )
    await message.reply_text(welcome_text)

@bot.on_message(filters.command("help"))  # Changed app to bot
async def send_help(client, message):
    help_text = (
        "🔍 How to use this bot:\n\n"
        "1. Send a YouTube link\n"
        "2. Wait for the video to download\n"
        "3. Receive your video\n\n"
        "⚠️ Limitations:\n"
        "• Maximum file size: 2GB (Telegram limit)\n"
        "• Supported formats: YouTube links only\n\n"
        "Note: Larger files may take longer to process and upload."
    )
    await message.reply_text(help_text)

@bot.on_message(filters.text & filters.regex(r"^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$"))  # Changed app to bot
async def handle_message(client, message):
    chat_id = message.chat.id
    url = message.text.strip()

    if not downloader.validate_url(url):
        await message.reply_text("❌ Please send a valid YouTube link.")
        return

    status_message = await message.reply_text("⏳ Processing your request...")

    info = downloader.get_video_info(url)
    if not info:
        await status_message.edit("❌ Could not fetch video information")
        return

    duration_str = downloader.format_duration(info['duration'])
    await status_message.edit(
        f"📥 Starting download:\n"
        f"🎥 {info['title']}\n"
        f"⏱ Duration: {duration_str}\n\n"
        f"Please wait while I process your video..."
    )

    video_path, error = await downloader.download_video(url, chat_id)
    if error:
        await status_message.edit(f"❌ {error}")
        return

    if os.path.exists(video_path):
        file_size = os.path.getsize(video_path)
        size_str = downloader.format_size(file_size)

        try:
            await status_message.edit(
                f"📤 Uploading video...\n"
                f"📦 Size: {size_str}\n"
                f"⏱ Duration: {duration_str}"
            )
            
            await client.send_video(
                chat_id,
                video_path,
                caption=f"🎥 {info['title']}\n⏱ Duration: {duration_str}\n📦 Size: {size_str}",
                supports_streaming=True
            )
            os.remove(video_path)
            await status_message.delete()
        except Exception as e:
            logger.error(f"Telegram API error for chat {chat_id}: {str(e)}")
            await status_message.edit(f"❌ An error occurred during upload: {str(e)}")
            if os.path.exists(video_path):
                os.remove(video_path)
    else:
        await status_message.edit("❌ Failed to process video. Please try again.")

if __name__ == "__main__":
    logger.info("Bot started")
    bot.run()  # Changed app.run() to bot.run()
