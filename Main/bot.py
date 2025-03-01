import os
import logging
import threading
import pymongo
import random
from PIL import Image
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from database.users_chats_db import db
from database.lazy_ffmpeg import take_screen_shot
from database.add import add_user_to_database
from plugins.settings.settings import *
from lazybot.forcesub import handle_force_subscribe
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI
from info import DOWNLOAD_LOCATION, AUTH_CHANNEL

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

# Dictionary to store user rename requests
rename_requests = {}

# Handle file upload
@bot.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def rename_start(client, message):
    file = getattr(message, message.media.value)
    
    rename_requests[message.chat.id] = {
        "file_id": file.file_id,
        "file_type": message.media.value
    }

    text = f"**📂 File Detected!**\n\n📌 **File Name:** `{file.file_name}`\n📏 **Size:** `{file.file_size}`\n\n🔹 Choose an option below:"
    buttons = [
        [InlineKeyboardButton("📝 Rename File", callback_data="rename_file")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# Handle rename request
@bot.on_callback_query(filters.regex("rename_file"))
async def rename_request(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    
    if chat_id not in rename_requests:
        return await callback_query.answer("⚠️ No file found for renaming!", show_alert=True)
    
    await callback_query.message.reply_text("📌 Send the new filename (with extension, e.g., `new_movie.mp4`).")
    rename_requests[chat_id]["action"] = "rename"

# Rename file instantly
@bot.on_message(filters.private & filters.text)
async def handle_rename(client, message):
    chat_id = message.chat.id

    if chat_id in rename_requests and rename_requests[chat_id].get("action") == "rename":
        new_filename = message.text
        file_info = rename_requests[chat_id]

        await message.reply_document(document=file_info["file_id"], file_name=new_filename)
        
        await message.reply_text(f"✅ File renamed to `{new_filename}`.")
        del rename_requests[chat_id]

# Caption Handling
@bot.on_message(filters.private & filters.command('set_caption'))
async def add_caption(client, message):
    if len(message.command) == 1:
       return await message.reply_text("**Give a caption to set.\nExample:** `/set_caption {filename}\n\n💾 Size: {filesize}\n\n⏰ Duration: {duration}`")
    caption = message.text.split(" ", 1)[1]
    await db.set_caption(message.from_user.id, caption=caption)
    await message.reply_text("✅ Caption saved successfully!")

@bot.on_message(filters.private & filters.command('del_caption'))
async def delete_caption(client, message):
    caption = await db.get_caption(message.from_user.id)  
    if not caption:
       return await message.reply_text("😔 No Caption found...")
    await db.set_caption(message.from_user.id, caption=None)
    await message.reply_text("✅ Your Caption has been deleted.")

@bot.on_message(filters.private & filters.command('see_caption'))
async def see_caption(client, message):
    caption = await db.get_caption(message.from_user.id)  
    if caption:
       await message.reply_text(f"**Your Caption:**\n\n`{caption}`")
    else:
       await message.reply_text("😔 No Caption found...")

# Thumbnail Handling
@bot.on_message(filters.private & filters.command(['view_thumb', 'view_thumbnail', 'vt']))
async def viewthumb(client, message):
    await add_user_to_database(client, message)
    if AUTH_CHANNEL:
      fsub = await handle_force_subscribe(client, message)
      if fsub == 400:
        return
    thumb = await db.get_thumbnail(message.from_user.id)
    if thumb:
       await client.send_photo(
	   chat_id=message.chat.id, 
	   photo=thumb,
       caption=f"Current thumbnail for direct renaming",
       reply_markup=InlineKeyboardMarkup([
           [InlineKeyboardButton("🗑️ Delete Thumbnail" , callback_data="deleteThumbnail")]
       ]))
    else:
        await message.reply_text("😔 No thumbnail found.")

@bot.on_message(filters.private & filters.command(['del_thumb', 'delete_thumb', 'dt']))
async def removethumb(client, message):
    await add_user_to_database(client, message)
    if AUTH_CHANNEL:
      fsub = await handle_force_subscribe(client, message)
      if fsub == 400:
        return
    await db.set_thumbnail(message.from_user.id, file_id=None)
    await message.reply_text("✅ Thumbnail deleted successfully.")

@bot.on_message(filters.private & filters.command(['set_thumbnail', 'set_thumb', 'st']))
async def addthumbs(client, message):
    replied = message.reply_to_message
    if not replied or not replied.photo:
        return await message.reply_text("❌ Reply to a photo to set it as a thumbnail.")
    await db.set_thumbnail(message.from_user.id, file_id=replied.photo.file_id)
    await message.reply_text("✅ Custom thumbnail set successfully!")

# Utility Functions
async def Gthumb01(bot, update):
    thumb_image_path = os.path.join(DOWNLOAD_LOCATION, f"{update.from_user.id}.jpg")
    db_thumbnail = await db.get_lazy_thumbnail(update.from_user.id)
    if db_thumbnail:
        thumbnail = await bot.download_media(message=db_thumbnail, file_name=thumb_image_path)
        Image.open(thumbnail).convert("RGB").save(thumbnail)
        img = Image.open(thumbnail)
        img.resize((100, 100))
        img.save(thumbnail, "JPEG")
    else:
        thumbnail = None
    return thumbnail

async def Mdata01(download_directory):
    metadata = extractMetadata(createParser(download_directory))
    if metadata:
        return (
            metadata.get("width") if metadata.has("width") else 0,
            metadata.get("height") if metadata.has("height") else 0,
            metadata.get("duration").seconds if metadata.has("duration") else 0
        )
    return 0, 0, 0

async def Mdata02(download_directory):
    metadata = extractMetadata(createParser(download_directory))
    if metadata:
        return (
            metadata.get("width") if metadata.has("width") else 0,
            metadata.get("duration").seconds if metadata.has("duration") else 0
        )
    return 0, 0

async def Mdata03(download_directory):
    metadata = extractMetadata(createParser(download_directory))
    if metadata:
        return metadata.get("duration").seconds if metadata.has("duration") else 0
    return 0

# Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Start web server in background
threading.Thread(target=run).start()

# Run the bot
bot.run()
