import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- CONFIGURATION (Loads from Environment Variables) ---
API_ID = int(os.environ.get("API_ID", "YOUR_API_ID"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL", "YOUR_MONGO_URL")

# Render gives a specific PORT, so we must use it
PORT = int(os.environ.get("PORT", 8080))
HOST = "0.0.0.0"

# Automatically detect URL if on Render, otherwise use local
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
URL = RENDER_EXTERNAL_URL if RENDER_EXTERNAL_URL else f"http://{HOST}:{PORT}"

# --- DATABASE ---
# Add error handling for missing Mongo URL
if not MONGO_URL:
    print("❌ Error: MONGO_URL is missing!")
    exit(1)

db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["StreamBot"]
collection = db["files"]

# --- BOT ---
app = Client(
    "stream_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- WEB SERVER ---
routes = web.RouteTableDef()

@routes.get("/")
async def root_route(request):
    return web.Response(text="Stream Server is Running!")

@routes.get("/stream/{log_id}")
async def stream_handler(request):
    try:
        log_id = request.match_info["log_id"]
        
        # Validate log_id
        file_data = await collection.find_one({"_id": log_id})
        if not file_data:
            return web.Response(status=404, text="File not found in DB")

        file_id = file_data["file_id"]
        file_name = file_data.get("file_name", "video.mp4")
        
        # Simple generator to yield chunks from Pyrogram
        # Note: This allows downloading but 'seeking' (skipping forward) 
        # is complex and not fully supported in this simple implementation.
        async def media_generator():
            try:
                # stream=True yields chunks without downloading to disk
                async for chunk in app.get_file(file_id, download=True):
                    yield chunk
            except Exception as e:
                print(f"Stream Error: {e}")

        headers = {
            "Content-Type": "application/octet-stream", # Generic binary type
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }

        return web.Response(body=media_generator(), headers=headers)

    except Exception as e:
        print(f"Web Error: {e}")
        return web.Response(status=500, text="Internal Server Error")

# --- BOT COMMANDS ---

@app.on_message(filters.command("start"))
async def start_cmd(_, message):
    await message.reply_text("👋 Send me a video or file to get a stream link!")

@app.on_message(filters.video | filters.document)
async def media_handler(_, message: Message):
    media = message.video or message.document or message.audio

    # Create a unique ID
    log_id = f"{message.from_user.id}_{int(time.time())}"

    # Save to Database
    await collection.insert_one({
        "_id": log_id,
        "file_id": media.file_id,
        "file_name": media.file_name or "unknown_file",
        "file_size": media.file_size,
        "mime_type": getattr(media, "mime_type", "video/mp4")
    })

    stream_link = f"{URL}/stream/{log_id}"

    await message.reply_text(
        f"✅ **File Saved!**\n\n📂 Name: `{media.file_name}`\n🔗 Link: `{stream_link}`",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Download / Stream", url=stream_link)]]
        )
    )

# --- RUNNER ---
async def start_services():
    print("🚀 Starting Bot...")
    await app.start()
    print("🤖 Bot Started!")

    app_runner = web.AppRunner(web.Application())
    # Register the routes to the app
    server_app = web.Application()
    server_app.add_routes(routes)
    
    runner = web.AppRunner(server_app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    print(f"🌍 Web Server running at {URL}")
    
    # Keep the script running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        print("Stopping services...")
        
