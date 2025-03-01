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

# Store user modifications
user_requests = {}

# Detect forwarded files
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
        "caption": caption
    }

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Rename File", callback_data="rename_file")],
        [InlineKeyboardButton("✅ Done", callback_data="done")]
    ])

    await message.reply_text(
        f"📂 **File Detected:** `{file_name}`\n\nChoose an option below:",
        reply_markup=buttons
    )

# Handle Callbacks
@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    if chat_id not in user_requests:
        return await callback_query.answer("⚠️ No file found!", show_alert=True)

    action = callback_query.data
    user_requests[chat_id]["action"] = action

    if action == "rename_file":
        await callback_query.message.reply_text("📌 Send the new filename (with extension, e.g., `new_movie.mp4`).")
    elif action == "done":
        await process_final_file(client, chat_id, callback_query.message)

    await callback_query.answer()

# Handle Text Input for Filename
@bot.on_message(filters.text)
async def handle_text_input(client, message: Message):
    chat_id = message.chat.id

    if chat_id not in user_requests or "action" not in user_requests[chat_id]:
        return

    action = user_requests[chat_id]["action"]

    if action == "rename_file":
        new_filename = message.text
        user_requests[chat_id]["file_name"] = new_filename
        await message.reply_text(f"✅ File will be renamed to `{new_filename}`.\n\nClick **Done** when ready.")

    user_requests[chat_id]["action"] = None  # Reset action

# Process and Send Renamed File FAST
async def process_final_file(client, chat_id, message):
    if chat_id not in user_requests:
        return await message.reply_text("⚠️ No file found!")

    data = user_requests[chat_id]
    
    # Copy the file instantly with a new name
    await client.copy_message(
        chat_id,
        from_chat_id=chat_id,
        message_id=message.message_id,
        caption=f"📂 **Renamed File:** `{data['file_name']}`"
    )

    await message.reply_text("✅ File renamed instantly!")

    user_requests.pop(chat_id, None)

# Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Start web server in a separate thread
threading.Thread(target=run).start()

# Run the bot
bot.run()
    
