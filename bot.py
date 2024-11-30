from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ChatJoinRequest,
    Message
)
from pyrogram.errors import (
    FloodWait, 
    UserIsBlocked, 
    PeerIdInvalid
)
from pyrogram.enums import ChatType
import asyncio
import random
from datetime import datetime
import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Initialize bot with your credentials
app = Client(
    "auto_approver_bot",
    mongo_uri = os.environ.get("MONGO_URI")
    api_id=os.environ.get("TELEGRAM_API_ID"),
    api_hash=os.environ.get("TELEGRAM_API_HASH"),
    bot_token=os.environ.get("TELEGRAM_BOT_TOKEN")
)

class Database:
    def __init__(self, mongo_uri):
        """
        Initialize MongoDB database connection
        
        :param mongo_uri: MongoDB connection string
        """
        try:
            # Configure logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger(__name__)

            # Connect to MongoDB
            self.client = MongoClient(mongo_uri)
            
            # Select the database
            self.db = self.client.ApproveBot

            # Define collections
            self.users_collection = self.db.users
            self.channels_collection = self.db.channels
            self.groups_collection = self.db.groups

            # Test connection
            self.client.admin.command('ping')
            self.logger.info("Successfully connected to MongoDB")

        except ConnectionFailure:
            self.logger.error("Failed to connect to MongoDB. Check your connection string.")
            raise
        except Exception as e:
            self.logger.error(f"An error occurred while setting up MongoDB: {e}")
            raise

    def add_user(self, user_id: int, username: str):
        """
        Add a new user or update existing user in the database
        
        :param user_id: Telegram user ID
        :param username: Telegram username
        """
        try:
            # Upsert operation: insert if not exists, update if exists
            self.users_collection.update_one(
                {'user_id': user_id},
                {'$set': {
                    'username': username,
                    'last_seen': datetime.now()
                }},
                upsert=True
            )
            self.logger.info(f"User {user_id} added/updated successfully")
        except PyMongoError as e:
            self.logger.error(f"Error adding user {user_id}: {e}")

    def add_channel(self, user_id: int, channel_name: str, chat_id: int):
        """
        Add a channel to the database
        
        :param user_id: ID of user who added the channel
        :param channel_name: Name of the channel
        :param chat_id: Telegram chat ID of the channel
        """
        try:
            # Upsert operation for channels
            self.channels_collection.update_one(
                {'chat_id': chat_id},
                {'$set': {
                    'name': channel_name,
                    'added_by': user_id,
                    'added_date': datetime.now()
                }},
                upsert=True
            )
            self.logger.info(f"Channel {channel_name} added successfully")
        except PyMongoError as e:
            self.logger.error(f"Error adding channel {channel_name}: {e}")

    def add_group(self, user_id: int, group_name: str, group_id: int):
        """
        Add a group to the database
        
        :param user_id: ID of user who added the group
        :param group_name: Name of the group
        :param group_id: Telegram chat ID of the group
        """
        try:
            # Upsert operation for groups
            self.groups_collection.update_one(
                {'chat_id': group_id},
                {'$set': {
                    'name': group_name,
                    'added_by': user_id,
                    'added_date': datetime.now()
                }},
                upsert=True
            )
            self.logger.info(f"Group {group_name} added successfully")
        except PyMongoError as e:
            self.logger.error(f"Error adding group {group_name}: {e}")

    def get_all_users(self):
        """
        Retrieve all users from the database
        
        :return: List of user IDs
        """
        try:
            users = list(self.users_collection.find({}, {'user_id': 1}))
            return [user['user_id'] for user in users]
        except PyMongoError as e:
            self.logger.error(f"Error retrieving users: {e}")
            return []

    def get_all_groups(self):
        """
        Retrieve all group chat IDs from the database
        
        :return: List of group chat IDs
        """
        try:
            groups = list(self.groups_collection.find({}, {'chat_id': 1}))
            return [group['chat_id'] for group in groups]
        except PyMongoError as e:
            self.logger.error(f"Error retrieving groups: {e}")
            return []

    def __del__(self):
        """
        Close MongoDB connection when object is deleted
        """
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("MongoDB connection closed")

# Replace the old database initialization
db = Database(os.environ.get("MONGO_URI"))

# Keyboard Generators
def get_welcome_keyboard():
    bot_username = "AutoAccepterSmartBot"  # Replace with your bot's username
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add me to your channel", url=f"https://t.me/{bot_username}?startchannel=true")],
        [InlineKeyboardButton("➕ Add me to your Group", url=f"https://t.me/{bot_username}?startgroup=true")],
        [
            InlineKeyboardButton("👥 Support", url="https://t.me/SmokieOfficial"),
            InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/Hmm_Smokie")
        ]
    ])

def get_approval_keyboard(support_channel):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Join Support Channel", url=support_channel)]
    ])

# Command Handlers
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        db.add_user(user_id, username)
        
        welcome_text = (
           "👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐭𝐡𝐞 𝐀𝐮𝐭𝐨 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐫 𝐁𝐨𝐭\n\n"

            "ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢʀᴏᴜᴘ ᴍᴇᴍʙᴇʀꜱ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ.\n\n"

            "ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟꜱ ᴏʀ ɢʀᴏᴜᴘꜱ., ᴀɴᴅ ʟᴇᴛ ᴍᴇ ʜᴀɴᴅʟᴇ ᴛʜᴇ ʀᴇꜱᴛ!\n"
        )
        
        # Send video along with the welcome message
        video_url = "https://cdn.glitch.global/04a38d5f-8c30-452e-b709-33da5c74b12d/175446-853577055.mp4?v=1732257487908"
        await client.send_video(
            chat_id=user_id,
            video=video_url,
            caption=welcome_text,
            reply_markup=get_welcome_keyboard()
        )
    except Exception as e:
        print(f"Error in start_command: {str(e)}")
        await message.reply_text("An error occurred. Please try again later.")

# Join Request Handler
@app.on_chat_join_request()
async def handle_join_request(client, join_request: ChatJoinRequest):
    try:
        user_id = join_request.from_user.id
        chat_id = join_request.chat.id
        username = join_request.from_user.username or join_request.from_user.first_name
        chat_type = "channel" if join_request.chat.type == ChatType.CHANNEL else "group"
        chat_title = join_request.chat.title
        
        # Auto-approve the request
        await client.approve_chat_join_request(
            chat_id=chat_id,
            user_id=user_id
        )
        
        # Update database
        # Update database
        db.add_user(user_id, username)

        # Add channel or group for the user
        if chat_type == "channel":
            db.add_channel(user_id, chat_title, chat_id)
        else:
            db.add_group(user_id, chat_title, chat_id)
        
        # Send video and welcome message
        support_channel = "https://t.me/SmokieOfficial"  # Configure this
        
        formatted_username = f"@{username}" if join_request.from_user.username else username
        
        welcome_message = (
            f"𝐇𝐞𝐲 {formatted_username}! ✨\n\n"
            f"𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗼𝘂𝗿 𝗰𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆! 🎉\n"
            f"●︎ ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ ᴛᴏ ᴊᴏɪɴ **{chat_title}**!\n\n"
            f"ᴘʟᴇᴀꜱᴇ ᴄᴏɴꜱɪᴅᴇʀ ᴊᴏɪɴɪɴɢ ᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ ᴄʜᴀɴɴᴇʟ ᴀꜱ ᴡᴇʟʟ. "
        )
        
        video_url = "https://cdn.glitch.global/04a38d5f-8c30-452e-b709-33da5c74b12d/175446-853577055.mp4?v=1732257487908"
        await client.send_video(
            chat_id=user_id,
            video=video_url,
            caption=welcome_message,
            reply_markup=get_approval_keyboard(support_channel)
        )
    except Exception as e:
        print(f"Error in handle_join_request: {str(e)}")

@app.on_message(filters.new_chat_members)
async def on_new_chat_member(client, message: Message):
    try:
        bot_info = await client.get_me()  # Get bot's information
        if bot_info.id in [member.id for member in message.new_chat_members]:
            # Bot was added to the chat
            chat_id = message.chat.id
            chat_title = message.chat.title or "Unknown Chat"
            chat_type = "channel" if message.chat.type == ChatType.CHANNEL else "group"
            
            # Log or print debug info
            print(f"Bot added to {chat_type}: {chat_title} (ID: {chat_id})")

            # Update database with the channel or group info
            if chat_type == "channel":
                db.add_channel(
                    user_id=message.from_user.id,  # Admin or owner who added the bot
                    channel_name=chat_title,
                    chat_id=chat_id
                )
            else:  # chat_type == "group"
                db.add_group(
                    user_id=message.from_user.id,
                    group_name=chat_title,
                    group_id=chat_id
                )

            # Also add new members to user database
            for member in message.new_chat_members:
                # Skip adding the bot itself
                if member.id != bot_info.id:
                    username = member.username or member.first_name
                    db.add_user(member.id, username)

            # Send welcome message to the user who added the bot in private
            try:
                await client.send_message(
                    chat_id=message.from_user.id,
                    text=f"🤖 𝐁𝐨𝐭 𝐀𝐝𝐝𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!\n\n"
                         f"👥 𝐂𝐡𝐚𝐭 𝐍𝐚𝐦𝐞: **{chat_title}**\n"
                         f"🌟 𝐓𝐡𝐞 𝐛𝐨𝐭 𝐢𝐬 𝐧𝐨𝐰 𝐫𝐞𝐚𝐝𝐲 𝐭𝐨 𝐚𝐮𝐭𝐨𝐦𝐚𝐭𝐞 𝐭𝐡𝐢𝐬 {chat_type}."
                )
            except Exception as private_msg_error:
                print(f"Could not send private message: {private_msg_error}")

    except Exception as e:
        print(f"Error in on_new_chat_member: {str(e)}")

@app.on_message(filters.command("broadcast") & filters.user(1949883614))  # Replace with your Telegram user ID
async def broadcast_message(client, message: Message):
    """
    Broadcast a message or media to all users in the database.
    Supports text, media, documents, videos, images, polls, and inline buttons with full fidelity.
    """
    try:
        # Check if the message is a reply to another message or contains forwarded content
        if not message.reply_to_message and not message.media:
            await message.reply_text("Please reply to a message or send a message to broadcast.")
            return

        # Get the list of unique user IDs from the users database
        user_ids = db.get_all_users()
        
        # Randomize the order to avoid potential rate limits
        random.shuffle(user_ids)
        
        # Track broadcast statistics
        successful_broadcasts = 0
        failed_broadcasts = 0
        blocked_users = 0

        # Progress message
        progress_message = await message.reply_text("Starting broadcast... 0%")
        
        # Function to send a single broadcast
        async def send_broadcast(user_id):
            nonlocal successful_broadcasts, failed_broadcasts, blocked_users
            try:
                # Determine the source message (reply or original)
                source_msg = message.reply_to_message or message

                # Prepare common parameters
                caption = source_msg.caption or source_msg.text or ""
                reply_markup = source_msg.reply_markup

                # Media sending methods mapping
                media_methods = {
                    'photo': client.send_photo,
                    'video': client.send_video,
                    'document': client.send_document,
                    'audio': client.send_audio,
                    'voice': client.send_voice,
                    'animation': client.send_animation,
                    'sticker': client.send_sticker,
                    'video_note': client.send_video_note
                }

                # Detect and send media
                sent_message = None
                if source_msg.photo:
                    sent_message = await client.send_photo(
                        chat_id=user_id,
                        photo=source_msg.photo.file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif source_msg.video:
                    sent_message = await client.send_video(
                        chat_id=user_id,
                        video=source_msg.video.file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif source_msg.document:
                    sent_message = await client.send_document(
                        chat_id=user_id,
                        document=source_msg.document.file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif source_msg.audio:
                    sent_message = await client.send_audio(
                        chat_id=user_id,
                        audio=source_msg.audio.file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif source_msg.voice:
                    sent_message = await client.send_voice(
                        chat_id=user_id,
                        voice=source_msg.voice.file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif source_msg.animation:
                    sent_message = await client.send_animation(
                        chat_id=user_id,
                        animation=source_msg.animation.file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif source_msg.sticker:
                    sent_message = await client.send_sticker(
                        chat_id=user_id,
                        sticker=source_msg.sticker.file_id,
                        reply_markup=reply_markup
                    )
                elif source_msg.video_note:
                    sent_message = await client.send_video_note(
                        chat_id=user_id,
                        video_note=source_msg.video_note.file_id,
                        reply_markup=reply_markup
                    )
                else:
                    # If no media, send as a text message with keyboard
                    sent_message = await client.send_message(
                        chat_id=user_id,
                        text=caption,
                        reply_markup=reply_markup
                    )
                
                successful_broadcasts += 1
            except FloodWait as e:
                # Handle Telegram's flood wait
                print(f"Flood wait for {e.value} seconds")
                await asyncio.sleep(e.value)
                return False
            except (UserIsBlocked, PeerIdInvalid):
                blocked_users += 1
                return False
            except Exception as e:
                failed_broadcasts += 1
                print(f"Error broadcasting to {user_id}: {str(e)}")
                return False
            return True

        # Broadcast to users with rate limiting and error handling
        for i, user_id in enumerate(user_ids, 1):
            # Send broadcast
            result = await send_broadcast(user_id)
            
            # Update progress every 10 users
            if i % 10 == 0:
                progress = (i / len(user_ids)) * 100
                await progress_message.edit_text(f"Broadcast progress: {progress:.2f}%")
            
            # Add a small delay between broadcasts to avoid rate limits
            await asyncio.sleep(0.5)

        # Final report
        await progress_message.edit_text(
            f"📊 Broadcast Completed!\n\n"
            f"✅ Successful: {successful_broadcasts}\n"
            f"❌ Failed: {failed_broadcasts}\n"
            f"🚫 Blocked Users: {blocked_users}"
        )

    except Exception as e:
        await message.reply_text(f"Broadcast failed: {str(e)}")

@app.on_message(filters.command("broadcastgrp") & filters.user(1949883614))  # Replace with your Telegram user ID
async def broadcast_to_groups(client, message: Message):
    """
    Broadcast a message or media to all groups in the database.
    Supports full media types with captions and inline keyboards.
    """
    try:
        # Check if the message is a reply to another message or contains forwarded content
        if not message.reply_to_message and not message.media:
            await message.reply_text("Please reply to a message or send a message to broadcast to groups.")
            return

        # New code
        group_ids = db.get_all_groups()
        
        # Randomize the order to avoid potential rate limits
        random.shuffle(group_ids)
        
        # Track broadcast statistics
        successful_broadcasts = 0
        failed_broadcasts = 0
        restricted_groups = 0

        # Progress message
        progress_message = await message.reply_text("Starting group broadcast... 0%")
        
        # Function to send a single group broadcast
        async def send_group_broadcast(group_id):
            nonlocal successful_broadcasts, failed_broadcasts, restricted_groups
            try:
                # Determine the source message (reply or original)
                source_msg = message.reply_to_message or message

                # Prepare common parameters
                caption = source_msg.caption or source_msg.text or ""
                reply_markup = source_msg.reply_markup

                # Comprehensive media sending method
                try:
                    if source_msg.photo:
                        sent_message = await client.send_photo(
                            chat_id=group_id,
                            photo=source_msg.photo.file_id,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.video:
                        sent_message = await client.send_video(
                            chat_id=group_id,
                            video=source_msg.video.file_id,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.document:
                        sent_message = await client.send_document(
                            chat_id=group_id,
                            document=source_msg.document.file_id,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.audio:
                        sent_message = await client.send_audio(
                            chat_id=group_id,
                            audio=source_msg.audio.file_id,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.voice:
                        sent_message = await client.send_voice(
                            chat_id=group_id,
                            voice=source_msg.voice.file_id,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.animation:
                        sent_message = await client.send_animation(
                            chat_id=group_id,
                            animation=source_msg.animation.file_id,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.sticker:
                        # Stickers don't support captions, so send sticker first, then message
                        await client.send_sticker(
                            chat_id=group_id,
                            sticker=source_msg.sticker.file_id
                        )
                        sent_message = await client.send_message(
                            chat_id=group_id,
                            text=caption,
                            reply_markup=reply_markup
                        )
                    elif source_msg.video_note:
                        sent_message = await client.send_video_note(
                            chat_id=group_id,
                            video_note=source_msg.video_note.file_id
                        )
                        # Send caption as a separate message if exists
                        if caption:
                            await client.send_message(
                                chat_id=group_id,
                                text=caption,
                                reply_markup=reply_markup
                            )
                    else:
                        # Fallback to text message if no media
                        sent_message = await client.send_message(
                            chat_id=group_id,
                            text=caption,
                            reply_markup=reply_markup
                        )
                    
                    successful_broadcasts += 1
                    return True

                except Exception as send_error:
                    print(f"Error sending to group {group_id}: {str(send_error)}")
                    failed_broadcasts += 1
                    return False

            except Exception as e:
                print(f"Unexpected error with group {group_id}: {str(e)}")
                failed_broadcasts += 1
                return False

        # Broadcast to groups with rate limiting and error handling
        for i, group_id in enumerate(group_ids, 1):
            # Send broadcast
            result = await send_group_broadcast(group_id)
            
            # Update progress every 10 groups
            if i % 10 == 0:
                progress = (i / len(group_ids)) * 100
                await progress_message.edit_text(f"Group Broadcast progress: {progress:.2f}%")
            
            # Add a small delay between broadcasts to avoid rate limits
            await asyncio.sleep(0.5)

        # Final report
        await progress_message.edit_text(
            f"📊 Group Broadcast Completed!\n\n"
            f"✅ Successful: {successful_broadcasts}\n"
            f"❌ Failed: {failed_broadcasts}"
        )

    except Exception as e:
        await message.reply_text(f"Group Broadcast failed: {str(e)}")
        print(f"Unexpected broadcast error: {str(e)}")

print("Bot is running...")
app.run()
