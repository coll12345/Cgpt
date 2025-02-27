import os
import logging
import asyncio
import pymongo
import threading
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI
from flask import Flask
from imdb import IMDb

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

# Dictionary to store rename requests
rename_requests = {}

# Command: /start
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    buttons = [
        [InlineKeyboardButton('🎬 Movie Channel', url='https://t.me/real_MoviesAdda3')],
        [InlineKeyboardButton('🔍 Help', url=f"https://t.me/{client.me.username}?start=help")],
    ]
    await message.reply_text(
        "👋 Hello! I am an Auto-Filter Bot.\n\n"
        "I can help you find movies and rename files. Use /help to see my commands.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Detect forwarded movies and show rename options
@bot.on_message(filters.document | filters.video | filters.audio)
async def detect_movie_forward(client, message):
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

    rename_requests[message.chat.id] = {
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

# Handle rename, caption edit, and thumbnail update
@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    if chat_id not in rename_requests:
        return await callback_query.answer("⚠️ No file found!", show_alert=True)

    if callback_query.data == "rename_file":
        await callback_query.message.reply_text("📌 Send the new filename (including extension, e.g., `new_movie.mp4`)")
        rename_requests[chat_id]["action"] = "rename"

    elif callback_query.data == "change_thumb":
        await callback_query.message.reply_text("📌 Send a new thumbnail image.")
        rename_requests[chat_id]["action"] = "thumbnail"

    elif callback_query.data == "edit_caption":
        await callback_query.message.reply_text("📌 Send the new caption.")
        rename_requests[chat_id]["action"] = "caption"

    await callback_query.answer()

# Handle text input for renaming or caption changing
@bot.on_message(filters.text & filters.private)
async def handle_text_input(client, message):
    chat_id = message.chat.id

    if chat_id not in rename_requests or "action" not in rename_requests[chat_id]:
        return

    action = rename_requests[chat_id]["action"]
    data = rename_requests[chat_id]

    if action == "rename":
        new_filename = message.text
        await message.reply_document(document=data["file_id"], file_name=new_filename, caption=data["caption"])
        await message.reply_text(f"✅ File renamed to `{new_filename}`.")

    elif action == "caption":
        new_caption = message.text
        await message.reply_document(document=data["file_id"], caption=new_caption)
        await message.reply_text("✅ Caption updated successfully.")

    rename_requests.pop(chat_id, None)

# Web server for Koyeb (Prevents Bot from Sleeping)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

# Run the bot
bot.run()
        
