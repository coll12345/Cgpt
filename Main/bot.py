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


# File handling
@bot.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def rename_start(client, message):
    file = getattr(message, message.media.value)
    filesize = file.file_size  
    filename = file.file_name
    
    text = f"""\n⨳ *•.¸♡ L҉ΛＺ𝐲 ＭⓄｄ𝓔 ♡¸.•* ⨳\n\n**Please tell, what should I do with this file?**\n\n**🎞 File Name** :- `{filename}`\n\n⚙️ **File Size** :- `{filesize}`"""
    
    buttons = [[InlineKeyboardButton("📝 Rename File", callback_data="rename_file")],
               [InlineKeyboardButton("⨳  C L Ф S Ξ  ⨳", callback_data="cancel")]]
    
    await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))


# Handle rename request
@bot.on_callback_query(filters.regex("rename_file"))
async def rename_request(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    await callback_query.message.reply_text("📌 Send the new filename (including extension, e.g., `new_movie.mp4`)")
    user_requests[chat_id] = "rename"


# Handle renaming
@bot.on_message(filters.private & filters.text)
async def handle_rename(client, message):
    chat_id = message.chat.id
    
    if chat_id in user_requests and user_requests[chat_id] == "rename":
        new_filename = message.text
        file_id = message.reply_to_message.document.file_id
        
        await message.reply_document(document=file_id, file_name=new_filename)
        await message.reply_text(f"✅ File renamed to `{new_filename}`.")
        del user_requests[chat_id]


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
