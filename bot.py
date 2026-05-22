import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- ENV ----------------
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")

# ---------------- DB ----------------
conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer INTEGER,
    seller INTEGER,
    amount TEXT,
    status TEXT
)
""")
conn.commit()


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Elite Escrow Bot v2\n\n"
        "Use:\n"
        "/deal <amount>"
    )


# ---------------- CREATE DEAL ----------------
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /deal <amount>")
        return

    amount = context.args[0]
    buyer = update.effective_user.id

    cursor.execute(
        "INSERT INTO deals (buyer, seller, amount, status) VALUES (?, ?, ?, ?)",
        (buyer, None, amount, "PENDING")
    )
    conn.commit()

    deal_id = cursor.lastrowid

    keyboard = [
        [InlineKeyboardButton("🤝 Accept Deal", callback_data=f"accept_{deal_id}")],
        [InlineKeyboardButton("❌ Cancel Deal", callback_data=f"cancel_{deal_id}")]
    ]

    await update.message.reply_text(
        f"💰 DEAL CREATED\n🆔 ID: {deal_id}\n💵 Amount: {amount}\n📌 Status: PENDING",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    action, deal_id = data.split("_")
    deal_id = int(deal_id)

    cursor.execute("SELECT buyer, seller, amount, status FROM deals WHERE id=?", (deal_id,))
    deal = cursor.fetchone()

    if not deal:
        await query.edit_message_text("❌ Deal not found")
        return

    buyer, seller, amount, status = deal


    # ---------------- ACCEPT ----------------
    if action == "accept":
        cursor.execute("UPDATE deals SET seller=?, status=? WHERE id=?", (query.from_user.id, "ACTIVE", deal_id))
        conn.commit()

        await query.edit_message_text(
            f"🤝 DEAL ACCEPTED\n🆔 ID: {deal_id}\n📌 Status: ACTIVE"
        )


    # ---------------- CANCEL ----------------
    elif action == "cancel":
        cursor.execute("UPDATE deals SET status=? WHERE id=?", ("CANCELLED", deal_id))
        conn.commit()

        await query.edit_message_text(
            f"⚠️ DEAL CANCELLED\n🆔 ID: {deal_id}"
        )

        # FINAL ONLY post
        if PROOF_CHANNEL:
            await context.bot.send_message(
                chat_id=PROOF_CHANNEL,
                text=f"⚠️ ESCROW CANCELLED\nID: {deal_id}\nAmount: {amount}"
            )


# ---------------- RELEASE (ADMIN ONLY) ----------------
async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only")
        return

    if not context.args:
        await update.message.reply_text("Usage: /release <id>")
        return

    deal_id = int(context.args[0])

    cursor.execute("SELECT buyer, seller, amount FROM deals WHERE id=?", (deal_id,))
    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("❌ Deal not found")
        return

    buyer, seller, amount = deal

    cursor.execute("UPDATE deals SET status=? WHERE id=?", ("COMPLETED", deal_id))
    conn.commit()

    msg = f"💸 ESCROW COMPLETED\nID: {deal_id}\nAmount: {amount}"

    await update.message.reply_text(msg)

    # FINAL ONLY post to channel
    if PROOF_CHANNEL:
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=msg
        )


# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("release", release))
app.add_handler(CallbackQueryHandler(button_handler))

print("🚀 Escrow Bot v2 (SQLite + Buttons) Running...")

app.run_polling()
