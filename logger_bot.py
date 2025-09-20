import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_IDS = {int(uid) for uid in os.environ.get("OWNER_IDS", "").split(",") if uid.strip().isdigit()}

# --- DB Setup ---
conn = sqlite3.connect("chatlogs.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  message_id INTEGER,
  user_id INTEGER,
  username TEXT,
  text TEXT,
  timestamp INTEGER
)
""")
conn.commit()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Hello! मैं NEET Logger Bot हूँ.\n\n"
        "⚠️ मैं इस group की सारी messages को log करता हूँ.\n"
        "📌 Commands:\n"
        "/get_history <number> - Last N messages देखें (Owner only)\n"
        "/myid - अपना Telegram ID देखें\n\n"
        "❗ केवल authorized users ही history access कर सकते हैं."
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    m = update.message
    c.execute(
        "INSERT INTO messages (chat_id, message_id, user_id, username, text, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (
            m.chat.id,
            m.message_id,
            m.from_user.id if m.from_user else None,
            getattr(m.from_user, "username", None),
            m.text or "",
            m.date.timestamp()
        )
    )
    conn.commit()

async def get_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in OWNER_IDS:
        await update.message.reply_text("❌ Permission denied.")
        return

    limit = 50
    if context.args:
        try:
            limit = int(context.args[0])
        except:
            pass

    chat_id = update.effective_chat.id
    rows = c.execute(
        "SELECT user_id, username, text FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
        (chat_id, limit)
    ).fetchall()

    if not rows:
        await update.message.reply_text("⚠️ No messages logged yet.")
        return

    text = []
    for uid, uname, msg in rows[::-1]:
        uname_display = uname or str(uid)
        text.append(f"{uname_display}: {msg}")
    out = "\n".join(text)

    if len(out) > 4000:
        await update.message.reply_document(document=bytes(out, "utf-8"), filename="history.txt")
    else:
        await update.message.reply_text(out)

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("get_history", get_history))
    app.add_handler(MessageHandler(filters.ALL & (~filters.StatusUpdate.ALL), log_message))

    print("✅ Bot is running...")
    app.run_polling()
