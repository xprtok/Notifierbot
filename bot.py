import asyncio
import logging
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- CONFIGURATION ---
API_ID = 36982189         # Get from my.telegram.org
API_HASH = "d3ec5feee7342b692e7b5370fb9c8db7" # Get from my.telegram.org
BOT_TOKEN = "8533775390:AAFKVMACsIswFhlCAIn4yX2dFAjHEL62qLk" # Get from BotFather
MONGO_URL = "mongodb+srv://pandaxleech:Noha9980@cluster0.zpmlqlx.mongodb.net/?appName=Cluster0"
CHANNEL_ID = -1003619964659 # Optional: Channel to store files for backup
HOST = "0.0.0.0"
PORT = 8080
URL = "https://notifierbot-6mw9.onrender.com" # The public URL of your server

# --- DATABASE SETUP ---
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["StreamBot"]
collection = db["files"]

# --- BOT SETUP ---
app = Client("stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- WEB SERVER ROUTES ---
routes = web.RouteTableDef()

@routes.get("/")
async def root_route(request):
    return web.Response(text="Stream Server is Running!")

@routes.get("/stream/{log_id}")
async def stream_handler(request):
    log_id = request.match_info['log_id']
    
    # 1. Get file details from MongoDB
    file_data = await collection.find_one({"_id": log_id})
    if not file_data:
        return web.Response(status=404, text="File not found")
    
    file_id = file_data['file_id']
    file_name = file_data.get('file_name', 'video.mp4')
    file_size = file_data.get('file_size', 0)

    # 2. Set Headers for Streaming
    headers = {
        'Content-Type': 'video/mp4', # Or generic 'application/octet-stream'
        'Content-Disposition': f'inline; filename="{file_name}"',
    }
    
    # Support for Range requests (seeking in video)
    # This is a simplified version; full Range support requires more complex header parsing
    if request.headers.get("Range"):
        headers['Content-Range'] = f'bytes 0-{file_size-1}/{file_size}'
        headers['Accept-Ranges'] = 'bytes'

    # 3. Stream from Telegram -> Server -> User
    resp = web.StreamResponse(status=200, headers=headers)
    await resp.prepare(request)

    # Using Pyrogram's stream_media utility
    # Note: We create a custom client session for streaming if needed, 
    # but here we use the main bot app to download chunks.
    async for chunk in app.stream_media(file_id):
        await resp.write(chunk)
        try:
        await collection.insert_one(file_data)
    except:
        pass
    
    return resp

# --- BOT COMMANDS ---

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 Send me a video file, and I will generate a stream link!")

@app.on_message(filters.video | filters.document)
async def media_handler(client, message: Message):
    # 1. Get File Info
    media = message.video or message.document
    file_id = media.file_id
    file_name = media.file_name
    file_size = media.file_size
    
    # 2. Generate a unique ID for the link (using current time + user ID)
    log_id = f"{message.from_user.id}_{int(time.time())}"
    
    # 3. Save to MongoDB
    await collection.insert_one({
        "_id": log_id,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "caption": message.caption or ""
    })
    
    # 4. Generate Link
    stream_link = f"{URL}/stream/{log_id}"
    
    await message.reply_text(
        f"✅ **File Saved!**\n\n📂 Name: `{file_name}`\n🔗 Stream Link:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch / Stream", url=stream_link)]
        ])
    )

# --- RUNNER ---
async def start_services():
    # Start Web Server
    server = web.Application()
    server.add_routes(routes)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"🌍 Web Server running at {URL}")

    # Start Telegram Bot
    print("🤖 Bot Started...")
    await app.start()
    
    # Keep the script running
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
