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

# Detect forwarded files
@bot.on_message(filters.document | filters.video | filters.audio)
async def detect_file(client, message):
    file_id = message.document.file_id if message.document else (
        message.video.file_id if message.video else message.audio.file_id
    )
    file_name = message.document.file_name if message.document else (
        "Video.mp4" if message.video else "Audio.mp3"
    )
    file_name = file_name.replace('_', ' ')  # Fix underscores

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

# Handle Callback Queries
@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    if chat_id not in user_requests:
        return await callback_query.answer("⚠️ No file found!", show_alert=True)

    action = callback_query.data
    user_requests[chat_id]["action"] = action

    if action == "rename_file":
        await callback_query.message.reply_text("📌 Send the new filename (with extension, e.g., `new movie.mp4`).")

    elif action == "change_thumb":
        await callback_query.message.reply_text("📌 Send a new thumbnail image.")

    elif action == "edit_caption":
        await callback_query.message.reply_text("📌 Send the new caption.")

    elif action == "done":
        await process_final_file(client, chat_id, callback_query.message)

    await callback_query.answer()

# Handle User Inputs (Text & Photo)
@bot.on_message(filters.text | filters.photo)
async def handle_text_input(client, message: Message):
    chat_id = message.chat.id

    if chat_id not in user_requests or "action" not in user_requests[chat_id]:
        return

    action = user_requests[chat_id]["action"]

    if action == "rename_file":
        new_filename = message.text.replace('_', ' ')  # Fix underscores
        user_requests[chat_id]["file_name"] = new_filename
        await message.reply_text(f"✅ File will be renamed to `{new_filename}`.\n\nClick **Done** when ready.")

    elif action == "edit_caption":
        new_caption = message.text
        user_requests[chat_id]["caption"] = new_caption
        await message.reply_text("✅ Caption updated.\n\nClick **Done** when ready.")

    elif action == "change_thumb" and message.photo:
        photo_path = await client.download_media(message.photo.file_id, file_name=f"{chat_id}_thumb.jpg")
        user_requests[chat_id]["thumbnail"] = photo_path
        await message.reply_text("✅ Thumbnail updated.\n\nClick **Done** when ready.")

    user_requests[chat_id]["action"] = None

# Process and Send Final File
async def process_final_file(client, chat_id, message):
    if chat_id not in user_requests:
        return await message.reply_text("⚠️ No file found!")

    data = user_requests[chat_id]

    # Download the original file
    temp_file_path = await client.download_media(data["file_id"], file_name=f"{DOWNLOAD_DIR}/{data['file_name']}")
    new_filename = data["file_name"]
    new_caption = data["caption"]
    thumbnail_path = data["thumbnail"]

    new_file_path = os.path.join(DOWNLOAD_DIR, new_filename)

    if temp_file_path != new_file_path:
        os.rename(temp_file_path, new_file_path)

    # Send the modified file
    await client.send_document(
        chat_id=chat_id,
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
