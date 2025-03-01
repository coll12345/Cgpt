import os
import logging
import asyncio
import pymongo
import threading
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

# Ensure a download directory exists
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Dictionary to store user modifications
user_requests = {}


# Handle file messages
@bot.on_message(filters.document | filters.video | filters.audio)
async def file_received(client, message):
    file_id = None
    file_name = None

    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
    elif message.video:
        file_id = message.video.file_id
        file_name = "Video.mp4"
    elif message.audio:
        file_id = message.audio.file_id
        file_name = "Audio.mp3"

    if not file_id:
        return await message.reply("⚠️ Could not detect a valid file.")

    # Store file details
    user_requests[message.chat.id] = {
        "file_id": file_id,
        "caption": message.caption or "No Caption",
        "file_name": file_name
    }

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Rename File", callback_data="rename_file")],
        [InlineKeyboardButton("🖼 Change Thumbnail", callback_data="change_thumb")],
        [InlineKeyboardButton("📝 Edit Caption", callback_data="edit_caption")]
    ])

    await message.reply_text(
        f"**Movie Detected:** `{file_name}`\n\nChoose an option below:",
        reply_markup=buttons
    )


# Handle callback queries
@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    if chat_id not in user_requests:
        return await callback_query.answer("⚠️ No file found!", show_alert=True)

    data = user_requests[chat_id]

    if callback_query.data == "rename_file":
        await callback_query.message.reply_text("📌 Send the new filename (including extension, e.g., `new_movie.mp4`)")
        user_requests[chat_id]["action"] = "rename"

    elif callback_query.data == "change_thumb":
        await callback_query.message.reply_text("📌 Send a new thumbnail image.")
        user_requests[chat_id]["action"] = "thumbnail"

    elif callback_query.data == "edit_caption":
        await callback_query.message.reply_text("📌 Send the new caption.")
        user_requests[chat_id]["action"] = "caption"

    await callback_query.answer()


# Handle user input for renaming, caption editing, and thumbnail changing
@bot.on_message(filters.text)
async def handle_text_input(client, message):
    chat_id = message.chat.id

    if chat_id not in user_requests or "action" not in user_requests[chat_id]:
        return

    action = user_requests[chat_id]["action"]
    data = user_requests[chat_id]

    if action == "rename":
        new_filename = message.text
        await message.reply_document(document=data["file_id"], file_name=new_filename, caption=data["caption"])
        await message.reply_text(f"✅ File renamed to `{new_filename}`.")

    elif action == "caption":
        new_caption = message.text
        await message.reply_document(document=data["file_id"], caption=new_caption)
        await message.reply_text("✅ Caption updated successfully.")

    user_requests.pop(chat_id, None)


# Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Start the web server in a separate thread
threading.Thread(target=run).start()

# Run the bot
bot.run()
    
