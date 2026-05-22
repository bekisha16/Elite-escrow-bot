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
        "👋 Elite Escrow Bot v3\n\n"
        "Commands:\n"
        "/deal <amount>\n"
        "/release\n"
        "/cancel"
    )


# ---------------- DEAL ----------------
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

    await update.message.reply_text(
        f"💰 DEAL CREATED\n🆔 ID: {deal_id}\n💵 Amount: {amount}"
    )


# ---------------- REQUEST RELEASE ----------------
async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /release <deal_id>")
        return

    deal_id = int(context.args[0])

    cursor.execute("SELECT buyer, amount FROM deals WHERE id=?", (deal_id,))
    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("❌ Deal not found")
        return

    cursor.execute("UPDATE deals SET status=? WHERE id=?", ("RELEASE_REQUESTED", deal_id))
    conn.commit()

    buyer, amount = deal

    keyboard = [
        [InlineKeyboardButton("✅ Approve Release", callback_data=f"approve_release_{deal_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{deal_id}")]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📦 RELEASE REQUEST\n🆔 ID: {deal_id}\n💵 Amount: {amount}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("📨 Release request sent to admin")


# ---------------- REQUEST CANCEL ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /cancel <deal_id>")
        return

    deal_id = int(context.args[0])

    cursor.execute("SELECT buyer, amount FROM deals WHERE id=?", (deal_id,))
    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("❌ Deal not found")
        return

    cursor.execute("UPDATE deals SET status=? WHERE id=?", ("CANCEL_REQUESTED", deal_id))
    conn.commit()

    buyer, amount = deal

    keyboard = [
        [InlineKeyboardButton("❌ Approve Cancel", callback_data=f"approve_cancel_{deal_id}")],
        [InlineKeyboardButton("🔄 Reject", callback_data=f"reject_{deal_id}")]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"⚠️ CANCEL REQUEST\n🆔 ID: {deal_id}\n💵 Amount: {amount}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("📨 Cancel request sent to admin")


# ---------------- ADMIN BUTTON HANDLER ----------------
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # ---------------- APPROVE RELEASE ----------------
    if data.startswith("approve_release_"):
        deal_id = int(data.split("_")[2])

        cursor.execute("SELECT buyer, amount FROM deals WHERE id=?", (deal_id,))
        deal = cursor.fetchone()

        if not deal:
            await query.edit_message_text("❌ Deal not found")
            return

        buyer, amount = deal

        cursor.execute("UPDATE deals SET status=? WHERE id=?", ("COMPLETED", deal_id))
        conn.commit()

        msg = f"💸 ESCROW COMPLETED\n🆔 ID: {deal_id}\n💵 Amount: {amount}"

        await query.edit_message_text(msg)

        if PROOF_CHANNEL:
            await context.bot.send_message(chat_id=PROOF_CHANNEL, text=msg)


    # ---------------- APPROVE CANCEL ----------------
    elif data.startswith("approve_cancel_"):
        deal_id = int(data.split("_")[2])

        cursor.execute("SELECT buyer, amount FROM deals WHERE id=?", (deal_id,))
        deal = cursor.fetchone()

        if not deal:
            await query.edit_message_text("❌ Deal not found")
            return

        buyer, amount = deal

        cursor.execute("UPDATE deals SET status=? WHERE id=?", ("CANCELLED", deal_id))
        conn.commit()

        msg = f"⚠️ ESCROW CANCELLED\n🆔 ID: {deal_id}\n💵 Amount: {amount}"

        await query.edit_message_text(msg)

        if PROOF_CHANNEL:
            await context.bot.send_message(chat_id=PROOF_CHANNEL, text=msg)


    # ---------------- REJECT ----------------
    elif data.startswith("reject_"):
        await query.edit_message_text("❌ Request rejected by admin")


# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(CallbackQueryHandler(admin_buttons))

print("🚀 Escrow Bot v3 Running...")

app.run_polling()
