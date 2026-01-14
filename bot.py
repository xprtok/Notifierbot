import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- CONFIGURATION ---
API_ID = 12345678                # ✅ REQUIRED
API_HASH = "API_HASH_HERE"
BOT_TOKEN = "BOT_TOKEN_HERE"
MONGO_URL = "MONGO_URL_HERE"

HOST = "0.0.0.0"
PORT = 8080
URL = "https://notifierbot-6mw9.onrender.com"

# --- DATABASE ---
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

# --- WEB ---
routes = web.RouteTableDef()

@routes.get("/")
async def root_route(request):
    return web.Response(text="Stream Server is Running!")

@routes.get("/stream/{log_id}")
async def stream_handler(request):
    log_id = request.match_info["log_id"]

    file_data = await collection.find_one({"_id": log_id})
    if not file_data:
        return web.Response(status=404, text="File not found")

    file_id = file_data["file_id"]
    file_name = file_data.get("file_name", "video.mp4")

    headers = {
        "Content-Type": "video/mp4",
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Accept-Ranges": "bytes"
    }

    resp = web.StreamResponse(status=200, headers=headers)
    await resp.prepare(request)

    async for chunk in app.stream_media(file_id):
        await resp.write(chunk)

    return resp

# --- BOT COMMANDS ---

@app.on_message(filters.command("start"))
async def start_cmd(_, message):
    await message.reply_text("👋 Send me a video or file to get a stream link")

@app.on_message(filters.video | filters.document)
async def media_handler(_, message: Message):
    media = message.video or message.document

    log_id = f"{message.from_user.id}_{int(time.time())}"

    await collection.insert_one({
        "_id": log_id,
        "file_id": media.file_id,
        "file_name": media.file_name,
        "file_size": media.file_size
    })

    stream_link = f"{URL}/stream/{log_id}"

    await message.reply_text(
        f"✅ File Saved!\n\n📂 {media.file_name}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Stream", url=stream_link)]]
        )
    )

# --- RUN ---
async def start_services():
    # ✅ START BOT FIRST
    await app.start()
    print("🤖 Bot Started")

    server = web.Application()
    server.add_routes(routes)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    print(f"🌍 Web Server running at {URL}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_services())
