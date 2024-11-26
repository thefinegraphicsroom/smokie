from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ChatJoinRequest,
    Message,
    ChatPrivileges
)
from pyrogram.errors import (
    UserNotParticipant, 
    ChatAdminRequired, 
    FloodWait, 
    InputUserDeactivated, 
    UserIsBlocked, 
    PeerIdInvalid, 
    ChatWriteForbidden
)
from pyrogram.enums import ChatType, ChatMemberStatus
import asyncio
import json
from datetime import datetime
import os

# Initialize bot with your credentials
app = Client(
    "auto_approver_bot",
    api_id="26490815",
    api_hash="b99d8504b8812f9ec395ec61c010ac32",
    bot_token="7947156341:AAGEoZoklYxpbo5PyYqLjm5v4fSZFcfAUKM"
)

class Database:
    def __init__(self, 
                 users_path='users_database.json', 
                 channels_path='channels_database.json', 
                 groups_path='groups_database.json'):
        self.users_path = users_path
        self.channels_path = channels_path
        self.groups_path = groups_path
        
        # Initialize data dictionaries
        self.users = {}
        self.channels = {}
        self.groups = {}
        
        # Load existing data
        self.load_data()
    
    def load_data(self):
        # Load users data
        try:
            if os.path.exists(self.users_path):
                with open(self.users_path, 'r') as f:
                    self.users = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.users = {}
            self.save_users_data()
        
        # Load channels data
        try:
            if os.path.exists(self.channels_path):
                with open(self.channels_path, 'r') as f:
                    self.channels = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.channels = {}
            self.save_channels_data()
        
        # Load groups data
        try:
            if os.path.exists(self.groups_path):
                with open(self.groups_path, 'r') as f:
                    self.groups = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.groups = {}
            self.save_groups_data()
    
    def save_users_data(self):
        with open(self.users_path, 'w') as f:
            json.dump(self.users, f, indent=4)
    
    def save_channels_data(self):
        with open(self.channels_path, 'w') as f:
            json.dump(self.channels, f, indent=4)
    
    def save_groups_data(self):
        with open(self.groups_path, 'w') as f:
            json.dump(self.groups, f, indent=4)
    
    def add_user(self, user_id: int, username: str):
        """Add a new user or update existing user"""
        user_str_id = str(user_id)
        
        if user_str_id not in self.users:
            self.users[user_str_id] = {
                'username': username,
                'joined_date': str(datetime.now()),
                'interactions': []
            }
            
            # Add join request interaction
            self._add_user_interaction(user_id, 'join_request')
            
            self.save_users_data()
    
    def add_channel(self, user_id: int, channel_name: str, chat_id: int):
        """Add a channel to channels database"""
        channel_str_id = str(chat_id)
        
        if channel_str_id not in self.channels:
            self.channels[channel_str_id] = {
                'name': channel_name,
                'added_date': str(datetime.now()),
                'members': [str(user_id)]
            }
        else:
            # Prevent duplicate user entries
            if str(user_id) not in self.channels[channel_str_id]['members']:
                self.channels[channel_str_id]['members'].append(str(user_id))
        
        self.save_channels_data()
    
    def add_group(self, user_id: int, group_name: str, group_id: int):
        """Add a group to groups database"""
        group_str_id = str(group_id)
        
        if group_str_id not in self.groups:
            self.groups[group_str_id] = {
                'name': group_name,
                'added_date': str(datetime.now()),
                'members': [str(user_id)]
            }
        else:
            # Prevent duplicate user entries
            if str(user_id) not in self.groups[group_str_id]['members']:
                self.groups[group_str_id]['members'].append(str(user_id))
        
        self.save_groups_data()
    
    def _add_user_interaction(self, user_id: int, interaction_type: str, details=None):
        """Add an interaction record for a user"""
        user_str_id = str(user_id)
        if user_str_id not in self.users:
            return
        
        interaction = {
            'type': interaction_type,
            'timestamp': str(datetime.now())
        }
        
        if details:
            interaction.update(details)
        
        if 'interactions' not in self.users[user_str_id]:
            self.users[user_str_id]['interactions'] = []
        
        self.users[user_str_id]['interactions'].append(interaction)
        self.save_users_data()

# Initialize database
db = Database()

# Keyboard Generators
def get_welcome_keyboard():
    bot_username = "AutoAccepterSmartBot"  # Replace with your bot's username
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add me to your channel", url=f"https://t.me/{bot_username}?startchannel=true")],
        [InlineKeyboardButton("➕ Add me to your Group", url=f"https://t.me/{bot_username}?startgroup=true")],
        [
            InlineKeyboardButton("👥 Support", url="https://t.me/SmokieOfficial"),
            InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/hmm_Smokie")
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

            # Inform the admin/owner about the bot's setup
            await message.reply_text(
                f"🤖 𝐁𝐨𝐭 𝐀𝐝𝐝𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!\n\n"
                f"👥 𝐂𝐡𝐚𝐭 𝐍𝐚𝐦𝐞: **{chat_title}**\n"
                f"✔️ 𝐓𝐡𝐞 𝐛𝐨𝐭 𝐢𝐬 𝐧𝐨𝐰 𝐫𝐞𝐚𝐝𝐲 𝐭𝐨 𝐚𝐮𝐭𝐨𝐦𝐚𝐭𝐞 𝐭𝐡𝐢𝐬 {chat_type}."
            )
    except Exception as e:
        print(f"Error in on_new_chat_member: {str(e)}")

print("Bot is running...")
app.run()
