import os
import logging
import threading
import pymongo
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI
from flask import Flask

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
    
    # Store file details
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

        # Send the renamed file instantly
        await message.reply_document(document=file_info["file_id"], file_name=new_filename)
        
        await message.reply_text(f"✅ File renamed to `{new_filename}`.")
        del rename_requests[chat_id]

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
