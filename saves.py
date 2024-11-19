import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple, Union, Dict
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import re
from urllib.parse import urlparse, urljoin, unquote
import json
import yt_dlp
import asyncio
from telegram.constants import ParseMode
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    TELEGRAM_TOKEN = "7060430437:AAH6NkmJ17Q09fXf6dPzM2ykmo7b8xDW5TQ"
    TEMP_DIR = Path("temp")
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Referer': 'https://www.pinterest.com/',
    }
    MAX_IMAGE_SIZE = {
        'width': 3000,
        'height': 3000
    }

@dataclass
class FacebookMedia:
    url: str
    file_path: Optional[str] = None
    title: Optional[str] = None
    media_type: str = 'video'

class FacebookDownloader:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        # Suppress yt-dlp logging
        yt_dlp.utils.std_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    def download_video(self, url: str) -> Optional[FacebookMedia]:
        """
        Download Facebook video or Reel
        
        Args:
            url (str): Facebook video URL
        
        Returns:
            Optional[FacebookMedia]: Downloaded media information
        """
        # Ensure download directory exists
        self.temp_dir.mkdir(exist_ok=True)
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(str(self.temp_dir), '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'no_color': True,
            'simulate': False,
            'nooverwrites': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Capture video information 
                info_dict = ydl.extract_info(url, download=True)
                
                # Get the filename
                filename = ydl.prepare_filename(info_dict)
                
                # Extract title
                title = info_dict.get('title', os.path.basename(filename))
                
                # Verify file exists
                if os.path.exists(filename):
                    return FacebookMedia(
                        url=url, 
                        file_path=filename, 
                        title=title
                    )
                else:
                    return None
        
        except Exception as e:
            logging.error(f"Facebook download error: {e}")
            return None
        
@dataclass
class PinterestMedia:
    url: str = ''
    media_type: str = 'image'
    width: int = 0
    height: int = 0
    fallback_urls: list = field(default_factory=list)
    
    def __post_init__(self):
        if self.fallback_urls is None:
            self.fallback_urls = []

class PinterestDownloader:
    def __init__(self):
        self.session = None
        self.pin_patterns = [
            r'/pin/(\d+)',
            r'pin/(\d+)',
            r'pin_id=(\d+)'
        ]
        
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=Config.HEADERS)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def extract_pin_id(self, url: str) -> Optional[str]:
        """Extract Pinterest pin ID from URL"""
        await self.init_session()
        
        if 'pin.it' in url:
            async with self.session.head(url, allow_redirects=True) as response:
                url = str(response.url)
        
        for pattern in self.pin_patterns:
            if match := re.search(pattern, url):
                return match.group(1)
        return None

    def get_highest_quality_image(self, image_url: str) -> str:
        """Convert image URL to highest quality version"""
        # Remove any existing dimensions and get original
        url = re.sub(r'/\d+x/|/\d+x\d+/', '/originals/', image_url)
        url = re.sub(r'\?.+$', '', url)  # Remove query parameters
        return url

    async def get_pin_data(self, pin_id: str) -> Optional[PinterestMedia]:
        """Get pin data using webpage method"""
        try:
            return await self.get_data_from_webpage(pin_id)
        except Exception as e:
            logger.error(f"Error getting pin data: {e}")
            return None

    async def get_data_from_api(self, pin_id: str) -> Optional[PinterestMedia]:
        """Get highest quality image data from Pinterest's API"""
        api_url = f"https://api.pinterest.com/v3/pidgets/pins/info/?pin_ids={pin_id}"
        
        async with self.session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()
                if pin_data := data.get('data', [{}])[0].get('pin'):
                    # Check for video first
                    if videos := pin_data.get('videos', {}).get('video_list', {}):
                        video_formats = list(videos.values())
                        if video_formats:
                            best_video = max(video_formats, key=lambda x: x.get('width', 0) * x.get('height', 0))
                            return PinterestMedia(
                                url=best_video.get('url'),
                                media_type='video',
                                width=best_video.get('width', 0),
                                height=best_video.get('height', 0)
                            )
                    
                    # Get highest quality image
                    if images := pin_data.get('images', {}):
                        # Try to get original image first
                        if orig_image := images.get('orig'):
                            image_url = self.get_highest_quality_image(orig_image.get('url'))
                            return PinterestMedia(
                                url=image_url,
                                media_type='image',
                                width=orig_image.get('width', 0),
                                height=orig_image.get('height', 0)
                            )
        return None

    async def get_data_from_webpage(self, pin_id: str) -> Optional[PinterestMedia]:
        """Get media data from webpage with enhanced parsing"""
        url = f"https://www.pinterest.com/pin/{pin_id}/"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                text = await response.text()
                
                # Look for video first
                video_matches = re.findall(r'"url":"([^"]*?\.mp4[^"]*)"', text)
                if video_matches:
                    video_url = unquote(video_matches[0].replace('\\/', '/'))
                    return PinterestMedia(
                        url=video_url,
                        media_type='video'
                    )

                # Look for high-quality image in meta tags
                image_patterns = [
                    r'<meta property="og:image" content="([^"]+)"',
                    r'"originImageUrl":"([^"]+)"',
                    r'"image_url":"([^"]+)"',
                ]
                
                for pattern in image_patterns:
                    if matches := re.findall(pattern, text):
                        for match in matches:
                            image_url = unquote(match.replace('\\/', '/'))
                            if any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                return PinterestMedia(
                                    url=self.get_highest_quality_image(image_url),
                                    media_type='image'
                                )
                
                # Try finding image in JSON data
                json_pattern = r'<script[^>]*?>\s*?({.+?})\s*?</script>'
                for json_match in re.finditer(json_pattern, text):
                    try:
                        data = json.loads(json_match.group(1))
                        if isinstance(data, dict):
                            # Look through nested dictionaries for image URLs
                            def find_image_url(d):
                                if isinstance(d, dict):
                                    for k, v in d.items():
                                        if isinstance(v, str) and any(ext in v.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                            return v
                                        elif isinstance(v, (dict, list)):
                                            result = find_image_url(v)
                                            if result:
                                                return result
                                elif isinstance(d, list):
                                    for item in d:
                                        result = find_image_url(item)
                                        if result:
                                            return result
                                return None

                            if image_url := find_image_url(data):
                                return PinterestMedia(
                                    url=self.get_highest_quality_image(image_url),
                                    media_type='image'
                                )
                    except json.JSONDecodeError:
                        continue

        return None

    

    async def get_data_from_mobile_api(self, pin_id: str) -> Optional[PinterestMedia]:
        """Get highest quality media from mobile API"""
        mobile_api_url = f"https://www.pinterest.com/_ngapi/pins/{pin_id}"
        
        headers = {**Config.HEADERS, 'Accept': 'application/json'}
        async with self.session.get(mobile_api_url, headers=headers) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    
                    # Check for video first
                    if video_data := data.get('videos', {}).get('video_list', {}):
                        best_video = max(
                            video_data.values(),
                            key=lambda x: x.get('width', 0) * x.get('height', 0)
                        )
                        if 'url' in best_video:
                            return PinterestMedia(
                                url=best_video['url'],
                                media_type='video',
                                width=best_video.get('width', 0),
                                height=best_video.get('height', 0)
                            )
                    
                    # Get highest quality image
                    if image_data := data.get('images', {}):
                        if orig_image := image_data.get('orig'):
                            image_url = self.get_highest_quality_image(orig_image.get('url'))
                            return PinterestMedia(
                                url=image_url,
                                media_type='image',
                                width=orig_image.get('width', 0),
                                height=orig_image.get('height', 0)
                            )
                except json.JSONDecodeError:
                    pass
        
        return None

class PinterestBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.downloader = PinterestDownloader()
        self.facebook_downloader = FacebookDownloader(Config.TEMP_DIR)
        Config.TEMP_DIR.mkdir(exist_ok=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            '''🔥 Welcome, you can download via bot:\n
Just send me a Link and I'll download it for you.\n
- Facebook videos / Facebook Reels
- Pinterest Images / Pinterest Videos

🚀 Send its link to start downloading media.'''
        )

    async def download_facebook(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Facebook URL messages with improved responsiveness"""
        url = update.message.text.strip()
        
        if 'facebook.com' not in url:
            await update.message.reply_text('Please send a valid Facebook link')
            return
        
        try:
            # Send initial processing message
            processing_message = await update.message.reply_text(
                "⏳ *Processing your request...*", 
                parse_mode=ParseMode.MARKDOWN
            )
        
            # Asynchronously download media to prevent blocking
            def download_media():
                return self.facebook_downloader.download_video(url)
            
            media_data = await asyncio.to_thread(download_media)
            
            if not media_data or not media_data.file_path:
                await processing_message.edit_text('Could not download media from this Facebook link.')
                return
            
            # Update status
            await processing_message.edit_text(
                "*Found ☑️ Downloading...\n\nPlease wait while I process your video...*", 
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send video with streaming support
            with open(media_data.file_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"Title: {media_data.title}" if media_data.title else None,
                    supports_streaming=True
                )
            
            # Delete processing message
            await processing_message.delete()
            
            # Cleanup
            os.remove(media_data.file_path)
            
        except Exception as e:
            logging.error(f"Error processing Facebook message: {e}")
            await processing_message.edit_text('An error occurred while processing your request.')

    async def download_pinterest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Pinterest URL messages with improved responsiveness"""
        url = update.message.text.strip()
        
        if not ('pinterest.com' in url or 'pin.it' in url):
            await update.message.reply_text('Please send a valid Pinterest link')
            return
        
        try:
            # Send initial processing message
            processing_message = await update.message.reply_text(
                "⏳ *Processing your request...*", 
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Extract pin ID asynchronously
            pin_id = await self.downloader.extract_pin_id(url)
            if not pin_id:
                await processing_message.edit_text('Invalid Pinterest URL. Please send a valid pin URL.')
                return
            
            # Get media data
            media_data = await self.downloader.get_pin_data(pin_id)
            if not media_data:
                await processing_message.edit_text('Could not find media in this Pinterest link.')
                return
            
            # Update status
            await processing_message.edit_text(
                "*Found ☑️ Downloading...\n\nPlease wait while I process your video...*", 
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Prepare file path
            file_path = Config.TEMP_DIR / f"temp_{update.message.chat_id}_{pin_id}"
            file_path = file_path.with_suffix('.mp4' if media_data.media_type == 'video' else '.jpg')
            
            # Asynchronous download with progress tracking
            async def download_file(url, file_path):
                async with self.downloader.session.get(url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        return True
                return False
            
            # Download media
            download_success = await download_file(media_data.url, file_path)
            
            if not download_success or not os.path.getsize(file_path):
                await processing_message.edit_text('Failed to download media. Please try again later.')
                return
            
            # Send media
            try:
                if media_data.media_type == "video":
                    await update.message.reply_video(
                        video=open(file_path, 'rb'),
                        supports_streaming=True
                    )
                else:
                    await update.message.reply_photo(
                        photo=open(file_path, 'rb')
                    )
                
                # Delete processing message
                await processing_message.delete()
                
            except Exception as e:
                logger.error(f"Send media error: {e}")
                await processing_message.edit_text('Failed to send media. Please try again later.')
            
            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await processing_message.edit_text('An error occurred while processing your request.')

    def run(self):
        """Start the bot"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & 
                (filters.Regex(r'pinterest\.com') | filters.Regex(r'pin\.it') |  # Pinterest filters
                 filters.Regex(r'facebook\.com')),  # Facebook filter
                self.handle_url_download
            )
        )
        
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def handle_url_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Centralized URL handling method"""
        url = update.message.text.strip()
        
        if 'pinterest.com' in url or 'pin.it' in url:
            await self.download_pinterest(update, context)
        elif 'facebook.com' in url:
            await self.download_facebook(update, context)
        else:
            await update.message.reply_text('Unsupported link type')

def main():
    token = os.getenv("TELEGRAM_TOKEN", Config.TELEGRAM_TOKEN)
    bot = PinterestBot(token)
    bot.run()

if __name__ == '__main__':
    main()