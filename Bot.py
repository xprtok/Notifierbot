import asyncio
import logging
import feedparser
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from keep_alive import keep_alive  # Imports the web server

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Configuration ---
# Remove 'os.environ.get' and use the string directly
TOKEN = os.environ.get"8533775390:AAFKVMACsIswFhlCAIn4yX2dfAjHEL62qLk"

# Google News RSS Base URL
RSS_BASE = "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en"

# Topics Dictionary
TOPICS = {
    "entertainment": "Entertainment",
    "technology": "Technology",
    "youtube": "YouTube",
    "celebrity": "Celebrity",
    "lifestyle": "Lifestyle",
    "wwe": "WWE",
    "netflix": "Netflix",
    "amazon_prime": "Amazon Prime",
    "global": "World News"
}

# --- Helper Function to Fetch News ---
def get_news(query):
    feed_url = RSS_BASE.format(query.replace(" ", "+"))
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        return "No news found at the moment."

    # Get top 5 articles
    messages = []
    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link
        messages.append(f"📰 <b>{title}</b>\n🔗 <a href='{link}'>Read Article</a>")
    
    return "\n\n".join(messages)

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💻 Technology", callback_data='technology'),
         InlineKeyboardButton("🎬 Entertainment", callback_data='entertainment')],
        [InlineKeyboardButton("📹 YouTube", callback_data='youtube'),
         InlineKeyboardButton("🌟 Celebrity", callback_data='celebrity')],
        [InlineKeyboardButton("🥊 WWE", callback_data='wwe'),
         InlineKeyboardButton("🧘 Lifestyle", callback_data='lifestyle')],
        [InlineKeyboardButton("📺 Netflix", callback_data='netflix'),
         InlineKeyboardButton("📦 Amazon Prime", callback_data='amazon_prime')],
        [InlineKeyboardButton("🌍 Global News", callback_data='global')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 <b>Welcome to the News Bot!</b>\n\nSelect a topic below to get the latest updates:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge the click
    
    topic_key = query.data
    topic_name = TOPICS.get(topic_key, "News")
    
    await query.edit_message_text(text=f"🔄 Fetching latest news for <b>{topic_name}</b>...", parse_mode='HTML')
    
    try:
        news_content = get_news(topic_name)
        # Send the news
        await query.message.reply_text(
            f"📢 <b>Latest {topic_name} News:</b>\n\n{news_content}",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        # Show the menu again
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("What else would you like to read?", reply_markup=reply_markup)
        
    except Exception as e:
        logging.error(f"Error fetching news: {e}")
        await query.message.reply_text("❌ An error occurred while fetching news.")

async def menu_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handles the "Back to Menu" button
    await start(update, context)

if __name__ == '__main__':
    # 1. Start the dummy web server for Render
    keep_alive()
    
    # 2. Start the Bot
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler('start', start))
        app.add_handler(CallbackQueryHandler(menu_reset, pattern='^start$'))
        app.add_handler(CallbackQueryHandler(button_handler))

        print("Bot is running...")
        app.run_polling()
