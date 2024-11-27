# Telegram Auto Approver Bot

## Overview

This Telegram bot automatically handles join requests for channels and groups, providing seamless member management and user onboarding. The bot offers features like automatic approval, user tracking, and broadcast capabilities.

## Features

- 🤖 Automatic Join Request Approval
- 📊 User and Chat Database Management
- 📨 Broadcast Functionality
- 🎉 Customized Welcome Messages
- 📊 User and Group Tracking

## Prerequisites

- Python 3.7+
- Pyrogram Library
- Telegram API Credentials
- Environment Variables

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/telegram-auto-approver-bot.git
cd telegram-auto-approver-bot
```

2. Install required dependencies:
```bash
pip install pyrogram tgcrypto
```

3. Set up environment variables:
```bash
export TELEGRAM_API_ID=your_api_id
export TELEGRAM_API_HASH=your_api_hash
export TELEGRAM_BOT_TOKEN=your_bot_token
```

## Configuration

- Modify `bot_username` in `get_welcome_keyboard()` function
- Update support channel links
- Replace owner/support contact IDs and usernames

## Environmental Variables

Required environment variables:
- `TELEGRAM_API_ID`: Your Telegram API ID
- `TELEGRAM_API_HASH`: Your Telegram API Hash
- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot Token

## Database

The bot uses JSON files to store:
- User information (`users_database.json`)
- Channel information (`channels_database.json`)
- Group information (`groups_database.json`)

## Main Functions

- `/start`: Bot initialization and welcome message
- `/broadcast`: Send messages to all users
- `/broadcastgrp`: Send messages to all groups
- Automatic join request handling

## Broadcast Capabilities

- Supports various media types
- Handles rate limits
- Provides broadcast progress tracking
- Comprehensive error handling

## Security and Permissions

- Broadcast commands restricted to specific user IDs
- Comprehensive error handling
- Logging for tracking bot activities

## Logging

Configured logging captures:
- Timestamp
- Log level
- Detailed error messages

## Customization

Easily customizable:
- Welcome messages
- Support links
- Keyboard layouts

## Error Handling

Robust error management including:
- FloodWait handling
- User blocking detection
- Invalid peer handling

## Contributions

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

[Specify your license, e.g., MIT License]

## Contact

- Telegram: https://t.me/hmm_Smokie
- GitHub: [Your GitHub Profile](https://github.com/yourusername)

---

**Note**: Always keep your API credentials and bot token confidential.
