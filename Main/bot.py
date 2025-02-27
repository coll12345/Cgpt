import os
import logging
import asyncio
import pymongo
import threading
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot client
bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Connect to MongoDB
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["AutoFilterBot"]

# Dictionary to store user actions
user_requests = {}

# Command: /start
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    buttons = [
        [InlineKeyboardButton('🎬 Movie Channel', url='https://t.me/real_MoviesAdda3')],
        [InlineKeyboardButton('🔍 Help', url=f"https://t.me/{client.me.username}?start=help")],
    ]
    await message.reply_text(
        "👋 Hello! I am an Auto-Filter & File Rename Bot.\n\n"
        "I can rename files, change thumbnails, and modify captions.\n\n"
        "Send me any file to begin!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Detect forwarded files (Documents, Videos, or Audios)
@bot.on_message(filters.document | filters.video | filters.audio)
async def detect_file(client, message):
    file_id = message.document.file_id if message.document else (
        message.video.file_id if message.video else message.audio.file_id
    )
    file_name = message.document.file_name if message.document else (
        "Video.mp4" if message.video else "Audio.mp3"
    )
    caption = message.caption or "No Caption"

    user_requests[message.chat.id] = {
        "file_id": file_id,
        "file_name": file_name,
        "caption": caption,
        "thumbnail": None
    }

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Rename File", callback_data="rename_file")],
        [InlineKeyboardButton("🖼 Change Thumbnail", callback_data="change_thumb")],
        [InlineKeyboardButton("📝 Edit Caption", callback_data="edit_caption")],
        [InlineKeyboardButton("✅ Done", callback_data="done")]
    ])

    await message.reply_text(
        f"📂 **File Detected:** `{file_name}`\n\nChoose an option below:",
        reply_markup=buttons
    )

# Handle Callback Buttons
@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    if chat_id not in user_requests:
        return await callback_query.answer("⚠️ No file found!", show_alert=True)

    if callback_query.data == "rename_file":
        await callback_query.message.reply_text("📌 Send the new filename (with extension, e.g., `new_movie.mp4`).")
        user_requests[chat_id]["action"] = "rename"

    elif callback_query.data == "change_thumb":
        await callback_query.message.reply_text("📌 Send a new thumbnail image.")
        user_requests[chat_id]["action"] = "thumbnail"

    elif callback_query.data == "edit_caption":
        await callback_query.message.reply_text("📌 Send the new caption.")
        user_requests[chat_id]["action"] = "caption"

    elif callback_query.data == "done":
        await process_final_file(client, chat_id, callback_query.message)

    await callback_query.answer()

# Handle Text & Photo Inputs
@bot.on_message(filters.text | filters.photo)
async def handle_user_input(client, message: Message):
    chat_id = message.chat.id

    if chat_id not in user_requests or "action" not in user_requests[chat_id]:
        return

    action = user_requests[chat_id]["action"]

    if action == "rename":
        new_filename = message.text
        user_requests[chat_id]["file_name"] = new_filename
        await message.reply_text(f"✅ File renamed to `{new_filename}`.\n\nNow click **Done**.")

    elif action == "caption":
        new_caption = message.text
        user_requests[chat_id]["caption"] = new_caption
        await message.reply_text("✅ Caption updated successfully.\n\nNow click **Done**.")

    elif action == "thumbnail" and message.photo:
        photo_file = await client.download_media(message.photo.file_id)
        user_requests[chat_id]["thumbnail"] = photo_file
        await message.reply_text("✅ Thumbnail updated successfully.\n\nNow click **Done**.")

    user_requests[chat_id]["action"] = None  # Reset action

# Process and Send Final File
async def process_final_file(client, chat_id, message):
    if chat_id not in user_requests:
        return await message.reply_text("⚠️ No file found!")

    data = user_requests[chat_id]

    # Download the original file
    temp_file = await client.download_media(data["file_id"])
    new_filename = data["file_name"]
    new_caption = data["caption"]
    thumbnail_path = data["thumbnail"]

    # Rename the file
    new_file_path = f"./downloads/{new_filename}"
    os.rename(temp_file, new_file_path)

    # Send the modified file
    await message.reply_document(
        document=new_file_path,
        caption=new_caption,
        thumb=thumbnail_path if thumbnail_path else None
    )

    await message.reply_text("✅ File processed successfully!")

    # Clean up
    os.remove(new_file_path)
    if thumbnail_path:
        os.remove(thumbnail_path)

    user_requests.pop(chat_id, None)

# Run the bot
bot.run()

