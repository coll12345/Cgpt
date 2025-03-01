import os
import logging
import threading
import pymongo
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI
from flask import Flask
from pyrogram import Client, filters
from database.users_chats_db import db
from pyrogram import Client, filters
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import random
import os
from PIL import Image


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

#another
@Client.on_message(filters.private & filters.command('set_caption'))
async def add_caption(client, message):
    if len(message.command) == 1:
       return await message.reply_text("**Note: Lazy_Mode active ✅\n\n__𝙶𝚒𝚟𝚎 𝚖𝚎 𝚊 𝚌𝚊𝚙𝚝𝚒𝚘𝚗 𝚝𝚘 𝚜𝚎𝚝.__\n\n𝙴𝚡𝚊𝚖𝚙𝚕𝚎:- `/set_caption {filename}\n\n💾 Size: {filesize}\n\n⏰ Duration: {duration}`**")
    caption = message.text.split(" ", 1)[1]
    await db.set_caption(message.from_user.id, caption=caption)
    await message.reply_text("__** 𝚈𝙾𝚄𝚁 𝙲𝙰𝙿𝚃𝙸𝙾𝙽 𝚂𝙰𝚅𝙴𝙳 𝚂𝚄𝙲𝙲𝙴𝚂𝚂𝙵𝚄𝙻𝙻𝚈 ✅**__")

    
@Client.on_message(filters.private & filters.command('del_caption'))
async def delete_caption(client, message):
    caption = await db.get_caption(message.from_user.id)  
    if not caption:
       return await message.reply_text("Note: Lazy_Mode active ✅\n\n😔**Sorry sweetheart ! No Caption found...**😔")
    await db.set_caption(message.from_user.id, caption=None)
    await message.reply_text("**** Your Caption deleted successfully**✅️")
                                       
@Client.on_message(filters.private & filters.command('see_caption'))
async def see_caption(client, message):
    caption = await db.get_caption(message.from_user.id)  
    if caption:
       await message.reply_text(f"**Note: Lazy_Mode active ✅\n\nYour Caption:-**\n\n`{caption}`")
    else:
       await message.reply_text("😔**Sorry ! No Caption found...**😔")
        
#other1
# the Strings used for this "thing"
from pyrogram import Client
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
logging.getLogger("pyrogram").setLevel(logging.WARNING)
from pyrogram import filters
from database.lazy_ffmpeg import take_screen_shot
from info import DOWNLOAD_LOCATION, AUTH_CHANNEL
from database.users_chats_db import db
from plugins.settings.settings import *
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ForceReply
from lazybot.forcesub import handle_force_subscribe
from database.add import add_user_to_database

@Client.on_message(filters.private & filters.command(['view_thumb','view_thumbnail','vt']))
async def viewthumb(client, message):
    if not message.from_user:
        return await message.reply_text("What the hell is this...")
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
           [InlineKeyboardButton("🗑️ ᴅᴇʟᴇᴛᴇ ᴛʜᴜᴍʙɴᴀɪʟ" , callback_data="deleteThumbnail")]
       ]))
    else:
        await message.reply_text("😔**Sorry ! No thumbnail found...**😔") 

@Client.on_message(filters.private & filters.command(['del_thumb','delete_thumb','dt']))
async def removethumb(client, message):
    if not message.from_user:
        return await message.reply_text("What the hell is this...")
    await add_user_to_database(client, message)
    if AUTH_CHANNEL:
      fsub = await handle_force_subscribe(client, message)
      if fsub == 400:
        return
    await db.set_thumbnail(message.from_user.id, file_id=None)
    await message.reply_text("**Okay sweetie, I deleted your custom thumbnail for direct renaming. Now I will apply default thumbnail. ✅️**✅️")

@Client.on_message(filters.private & filters.command(['set_thumbnail','set_thumb','st']))
async def addthumbs(client, message):
    replied = message.reply_to_message
    
    if not message.from_user:
        return await message.reply_text("What the hell is this...")
    
    await add_user_to_database(client, message)
    
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(client, message)
        if fsub == 400:
            return
        
    LazyDev = await message.reply_text("Please Wait ...")
        # Check if there is a replied message and it is a photo
    if replied and replied.photo:
        # Save the photo file_id as a thumbnail for the user
        await db.set_thumbnail(message.from_user.id, file_id=replied.photo.file_id)
        await LazyDev.edit("**✅ Custom thumbnail set successfully!**")
    else:
        await LazyDev.edit("**❌ Please reply to a photo to set it as a custom thumbnail.**")

@Client.on_message(filters.private & filters.command(['view_lazy_thumb','vlt']))
async def viewthumbnail(client, message):    
    if not message.from_user:
        return await message.reply_text("What the hell is this...")
    await add_user_to_database(client, message) 
    if AUTH_CHANNEL:
      fsub = await handle_force_subscribe(client, message)
      if fsub == 400:
        return   
    thumbnail = await db.get_lazy_thumbnail(message.from_user.id)
    if thumbnail is not None:
        await client.send_photo(
        chat_id=message.chat.id,
        photo=thumbnail,
        caption=f"ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ sᴀᴠᴇᴅ ᴛʜᴜᴍʙɴᴀɪʟ 🦠",
        reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🗑️ ᴅᴇʟᴇᴛᴇ ᴛʜᴜᴍʙɴᴀɪʟ", callback_data="deleteurlthumbnail")]]
                ),
        reply_to_message_id=message.id)
    else:
        await message.reply_text(text=f"ɴᴏ ᴛʜᴜᴍʙɴᴀɪʟ ғᴏᴜɴᴅ 🤒")

@Client.on_message(filters.private & filters.command(['del_lazy_thumb','delete_lazy_thumb','dlt']))
async def removethumbnail(client, message):
    if not message.from_user:
        return await message.reply_text("What the hell is this...")
    await add_user_to_database(client, message)
    if AUTH_CHANNEL:
      fsub = await handle_force_subscribe(client, message)
      if fsub == 400:
        return

    await db.set_lazy_thumbnail(message.from_user.id, thumbnail=None)
    await message.reply_text(
        "**🗑️ Okay baby, I deleted your custom thumbnail for url downloading. Now I will apply default thumbnail. ☑**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙ ᴄᴏɴғɪɢᴜʀᴇ sᴇᴛᴛɪɴɢs 🎨", callback_data="openSettings")]
        ])
    )

@Client.on_message(filters.private & filters.command(['set_lazy_thumb','set_lazy_thumbnail', 'slt']))
async def add_thumbnail(client, message):
    replied = message.reply_to_message
    
    if not message.from_user:
        return await message.reply_text("What the hell is this...")
    
    await add_user_to_database(client, message)
    
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(client, message)
        if fsub == 400:
            return
    
    editable = await message.reply_text("**👀 Processing...**")
    
    # Check if there is a replied message and it is a photo
    if replied and replied.photo:
        # Save the photo file_id as a thumbnail for the user
        await db.set_lazy_thumbnail(message.from_user.id, thumbnail=replied.photo.file_id)
        await editable.edit("**✅ Custom thumbnail set successfully!**")
    else:
        await editable.edit("**❌ Please reply to a photo to set it as a custom thumbnail.**")


async def Gthumb01(bot, update):
    thumb_image_path = DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
    db_thumbnail = await db.get_lazy_thumbnail(update.from_user.id)
    if db_thumbnail is not None:
        thumbnail = await bot.download_media(message=db_thumbnail, file_name=thumb_image_path)
        Image.open(thumbnail).convert("RGB").save(thumbnail)
        img = Image.open(thumbnail)
        img.resize((100, 100))
        img.save(thumbnail, "JPEG")
    else:
        thumbnail = None

    return thumbnail

async def Gthumb02(bot, update, duration, download_directory):
    thumb_image_path = DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
    db_thumbnail = await db.get_lazy_thumbnail(update.from_user.id)
    if db_thumbnail is not None:
        thumbnail = await bot.download_media(message=db_thumbnail, file_name=thumb_image_path)
    else:
        thumbnail = await take_screen_shot(download_directory, os.path.dirname(download_directory), random.randint(0, duration - 1))

    return thumbnail

async def Mdata01(download_directory):
          width = 0
          height = 0
          duration = 0
          metadata = extractMetadata(createParser(download_directory))
          if metadata is not None:
              if metadata.has("duration"):
                  duration = metadata.get('duration').seconds
              if metadata.has("width"):
                  width = metadata.get("width")
              if metadata.has("height"):
                  height = metadata.get("height")
          return width, height, duration

async def Mdata02(download_directory):
          width = 0
          duration = 0
          metadata = extractMetadata(createParser(download_directory))
          if metadata is not None:
              if metadata.has("duration"):
                  duration = metadata.get('duration').seconds
              if metadata.has("width"):
                  width = metadata.get("width")

          return width, duration

async def Mdata03(download_directory):

          duration = 0
          metadata = extractMetadata(createParser(download_directory))
          if metadata is not None:
              if metadata.has("duration"):
                  duration = metadata.get('duration').seconds

          return duration

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
