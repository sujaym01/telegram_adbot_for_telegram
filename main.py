from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request, send_from_directory
from dotenv import load_dotenv
import os, sqlite3, threading

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", ""))
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
CPA_LINK = os.getenv("CPA_LINK", "")

def init_db():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        points REAL DEFAULT 0,
        ads_watched INTEGER DEFAULT 0
    )
""")

    conn.commit()
    conn.close()

def get_user(user_id, username):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def update_user_points(user_id, points=1):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + ?, ads_watched = ads_watched + 1 WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username or "guest")
    keyboard = [[InlineKeyboardButton("📲 Open Dashboard", web_app=WebAppInfo(url=WEBAPP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome @{user.username or 'guest'}! Click below to open your dashboard.",
        reply_markup=reply_markup
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    points = get_balance(user_id)
    await update.message.reply_text(f"💰 Your current balance: {points:.2f} points")

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_points(user.id)
    await update.message.reply_text(
        f"🎥 Click to watch ad: {CPA_LINK}?ref={user.id}\n\nYou earned 1 point! ✅"
    )

web_app = Flask(__name__)

@web_app.route("/")
def serve_index():
    return send_from_directory("webapp", "index.html")

@web_app.route("/withdraw", methods=["POST"])
def withdraw():
    data = request.json
    uid = data.get("user_id")
    username = data.get("username")
    number = data.get("number")
    points = get_balance(uid)
    if ADMIN_ID:
        msg = f"💸 Withdraw Request\n👤 @{username} ({uid})\n📱 Number: {number}\n💰 Points: {points:.2f}"
        Bot(token=BOT_TOKEN).send_message(chat_id=ADMIN_ID, text=msg)
    return {"status": "ok"}

def run_web():
    web_app.run(host="0.0.0.0", port=8000)

def main():
    init_db()
    threading.Thread(target=run_web).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("watch", watch))
    print("🚀 Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
