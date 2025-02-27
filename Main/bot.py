import os
import logging
import asyncio
import pymongo
import threading
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# Command: /start
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    buttons = [
        [InlineKeyboardButton('🎬 Movie Channel', url='https://t.me/real_MoviesAdda3')],
        [InlineKeyboardButton('🔍 Help', url=f"https://t.me/{client.me.username}?start=help")],
    ]
    await message.reply_text(
        "👋 Hello! I am an Auto-Filter Bot.\n\n"
        "I can help you find movies and rename files. Use /help to see my commands.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Command: /filter (Add Manual Filter)
@bot.on_message(filters.command("filter") & filters.group)
async def add_filter(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/filter <keyword> - <reply_text>`")
        return
    
    text = message.text.split("-")
    keyword = text[0].strip().split(" ", 1)[1].lower()
    reply_text = text[1].strip()
    
    db.filters.insert_one({"keyword": keyword, "reply_text": reply_text})
    await message.reply_text(f"✅ Filter added for `{keyword}`")

# Command: /filters (View Filters)
@bot.on_message(filters.command("filters") & filters.group)
async def view_filters(client, message):
    filters_list = db.filters.find()
    text = "🔍 **Available Filters:**\n\n"
    
    for filt in filters_list:
        text += f"🔹 `{filt['keyword']}`\n"
    
    if text == "🔍 **Available Filters:**\n\n":
        text = "🚫 No filters found!"
    
    await message.reply_text(text)

# Command: /del (Delete a Filter)
@bot.on_message(filters.command("del") & filters.group)
async def delete_filter(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/del <keyword>`")
        return
    
    keyword = message.command[1].lower()
    result = db.filters.delete_one({"keyword": keyword})
    
    if result.deleted_count:
        await message.reply_text(f"✅ Filter `{keyword}` deleted!")
    else:
        await message.reply_text(f"❌ No filter found for `{keyword}`")

# Command: /imdb (Fetch Movie Info)
from imdb import IMDb

@bot.on_message(filters.command("imdb") & filters.group)
async def imdb_info(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/imdb <movie name>`")
        return
    
    movie_name = " ".join(message.command[1:])
    ia = IMDb()
    movies = ia.search_movie(movie_name)
    
    if not movies:
        await message.reply_text("🚫 Movie not found!")
        return
    
    movie = movies[0]
    ia.update(movie)
    
    title = movie.get("title", "N/A")
    year = movie.get("year", "N/A")
    rating = movie.get("rating", "N/A")
    plot = movie.get("plot outline", "N/A")
    
    imdb_link = f"https://www.imdb.com/title/tt{movie.movieID}/"
    
    text = f"🎬 **{title} ({year})**\n⭐ **Rating:** {rating}/10\n📜 **Plot:** {plot}\n🔗 [More Info]({imdb_link})"
    await message.reply_text(text, disable_web_page_preview=True)

# Command: /rename (File Renaming)
@bot.on_message(filters.command("rename") & filters.private)
async def rename_file(client, message):
    await message.reply_text("Send me a file with the new name.")

# Command: /stats (Show bot stats)
@bot.on_message(filters.command("stats") & filters.private)
async def bot_stats(client, message):
    user_count = db.users.count_documents({})
    await message.reply_text(f"📊 **Bot Stats:**\n👥 Users: {user_count}")

# Command: /users (Show user list)
@bot.on_message(filters.command("users") & filters.private)
async def users_list(client, message):
    users = db.users.find()
    text = "👥 **Users List:**\n\n"
    
    for user in users:
        text += f"🔹 {user['user_id']} - {user['username']}\n"
    
    if text == "👥 **Users List:**\n\n":
        text = "🚫 No users found!"
    
    await message.reply_text(text)

#new add server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Start the web server in a separate thread
threading.Thread(target=run).start()

#image rename code
from pyrogram import Client, filters
from pyrogram.types import InputMediaDocument, InputMediaPhoto

@app.on_message(filters.command("edit"))
async def edit_media(client, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a media message to edit its caption or image!")

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("Usage: /edit <new_caption> <image_url (optional)>")

    new_caption = args[1]
    new_image = args[2] if len(args) > 2 else None

    if message.reply_to_message.document:
        media = InputMediaDocument(
            media=message.reply_to_message.document.file_id,
            caption=new_caption
        )
    elif message.reply_to_message.photo:
        media = InputMediaPhoto(
            media=new_image if new_image else message.reply_to_message.photo.file_id,
            caption=new_caption
        )
    else:
        return await message.reply("Unsupported media type!")

    await message.reply_to_message.edit_media(media)
    await message.reply("Media updated successfully!")
    


# Run the bot
bot.run()
