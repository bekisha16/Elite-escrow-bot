import os
import sqlite3
import time

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


TOKEN = os.getenv("BOT_TOKEN")

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
    deal_message_id INTEGER,
    created_at REAL
)
""")

conn.commit()


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot works ✅")


# CREATE DEAL
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:
        await update.message.reply_text("Usage: /deal @seller @buyer amount method")
        return

    seller = context.args[0]
    buyer = context.args[1]
    amount = context.args[2]
    method = " ".join(context.args[3:])

    cursor.execute("""
    INSERT INTO deals (seller_username, buyer_username, amount, method, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (seller, buyer, amount, method, "PENDING", time.time()))

    conn.commit()

    deal_id = cursor.lastrowid

    msg = await update.message.reply_text(
        f"DEAL #{deal_id}\n"
        f"Seller: {seller}\n"
        f"Buyer: {buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n"
        f"Waiting activation..."
    )

    cursor.execute("UPDATE deals SET deal_message_id=? WHERE id=?", (msg.message_id, deal_id))
    conn.commit()


# SIMPLE ACTIVATE
async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to deal message")
        return

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, amount, method
    FROM deals WHERE deal_message_id=?
    """, (msg_id,))

    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("Deal not found")
        return

    deal_id, seller, buyer, amount, method = deal

    cursor.execute("""
    UPDATE deals SET status=?
    WHERE id=?
    """, ("ACTIVE", deal_id))

    conn.commit()

    await update.message.reply_text(
        f"DEAL ACTIVATED #{deal_id}\n\n"
        f"Seller: {seller}\n"
        f"Buyer: {buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n\n"
        f"Seller can now use /release"
    )


# RELEASE (SIMPLE)
async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to activated deal")
        return

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, status
    FROM deals WHERE deal_message_id=?
    """, (msg_id,))

    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("Deal not found")
        return

    deal_id, seller, buyer, status = deal

    if status != "ACTIVE":
        await update.message.reply_text("Deal not active")
        return

    sender = f"@{update.effective_user.username}"

    if sender != seller:
        await update.message.reply_text("Only seller can do this")
        return

    await update.message.reply_text(
        f"SELLER RELEASE REQUESTED\n\n"
        f"Buyer: {buyer}\n"
        f"Please confirm manually (no buttons in this version)."
    )


# APP
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("activate", activate))
app.add_handler(CommandHandler("release", release))

app.run_polling()
