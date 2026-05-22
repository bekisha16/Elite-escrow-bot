import os
import sqlite3
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [6138132255, 5635739078]

# ================= DB =================
conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_username TEXT,
    buyer_username TEXT,
    amount TEXT,
    method TEXT,
    status TEXT,
    action_type TEXT,
    deal_message_id INTEGER,
    created_at REAL,
    buyer_confirmed INTEGER DEFAULT 0,
    handled_by TEXT,
    action_locked INTEGER DEFAULT 0,
    activator_admin_id INTEGER
)
""")

conn.commit()

# ================= HELPERS =================
def clean_username(u):
    return (u or "").replace("@", "").replace("seller:", "").replace("buyer:", "").strip().lower()

def safe_user(user):
    return (user.username or str(user.id)).lower()

def deal_id_fmt(i):
    return f"#{i:03d}"

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Running")

# ================= DEAL =================
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seller = clean_username(context.args[0])
    buyer = clean_username(context.args[1])
    amount = context.args[2]
    method = " ".join(context.args[3:])

    cursor.execute(
        "INSERT INTO deals (seller_username, buyer_username, amount, method, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (seller, buyer, amount, method, "PENDING", time.time())
    )
    conn.commit()

    deal_id = cursor.lastrowid

    await update.message.reply_text(
        f"NEW DEAL {deal_id_fmt(deal_id)}\nSeller: @{seller}\nBuyer: @{buyer}"
    )

# ================= ACTIVATE =================
async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Not admin")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply required")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("SELECT id FROM deals WHERE deal_message_id=?", (msg_id,))
    deal = cursor.fetchone()

    if not deal:
        return await update.message.reply_text("Not found")

    deal_id = deal[0]

    cursor.execute(
        "UPDATE deals SET status=?, activator_admin_id=? WHERE id=?",
        ("ACTIVE", update.effective_user.id, deal_id)
    )
    conn.commit()

    await update.message.reply_text("Activated")

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("activate", activate))

app.run_polling()
app.run_polling()app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(
    CallbackQueryHandler(
        buyer_buttons,
        pattern="^(acc|rej)_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        admin_buttons,
        pattern="^adm_"
    )
)

app.run_polling()
