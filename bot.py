import os
import sqlite3
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes


# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")


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
    handled_by TEXT
)
""")

conn.commit()


# ================= HELPERS =================
def format_deal_id(deal_id: int):
    return f"#{deal_id:03d}"


def format_duration(start_time):
    seconds = int(time.time() - start_time)
    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escrow Bot Running ✅")


# ================= DEAL =================
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:
        await update.message.reply_text("Usage: /deal @seller @buyer amount method")
        return

    seller = context.args[0].replace("@", "")
    buyer = context.args[1].replace("@", "")

    amount = context.args[2]
    method = " ".join(context.args[3:])

    cursor.execute("""
    INSERT INTO deals (
        seller_username,
        buyer_username,
        amount,
        method,
        status,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (seller, buyer, amount, method, "PENDING", time.time()))

    conn.commit()

    deal_id = cursor.lastrowid

    # ================= GROUP MESSAGE =================
    await update.message.reply_text(
        f"🚨 NEW ESCROW DEAL 🚨\n\n"
        f"🆔 DEAL {format_deal_id(deal_id)}\n"
        f"👤 Seller: {seller}\n"
        f"👤 Buyer: {buyer}\n"
        f"💰 Amount: {amount}\n"
        f"💳 Method: {method}\n\n"
        f"👮 Admin has been notified"
    )

    # ================= ADMIN DM (ONLY HERE) =================
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🚨 NEW ESCROW DEAL 🚨\n\n"
            f"🆔 DEAL {format_deal_id(deal_id)}\n"
            f"👤 Seller: {seller}\n"
            f"👤 Buyer: {buyer}\n"
            f"💰 Amount: {amount}\n"
            f"💳 Method: {method}\n\n"
            f"👉 Please activate this deal in the group"
        )
    )


# ================= ACTIVATE =================
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

    cursor.execute("UPDATE deals SET status=? WHERE id=?", ("ACTIVE", deal_id))
    conn.commit()

    await update.message.reply_text(
        f"DEAL ACTIVATED {format_deal_id(deal_id)}\n\n"
        f"Seller: {seller}\n"
        f"Buyer: {buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n\n"
        f"Ready for escrow actions"
    )


# ================= SELLER ACTION =================
async def seller_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action):

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

    sender = update.effective_user.username or ""
    sender = sender.replace("@", "").lower()

    if sender != seller.lower():
        await update.message.reply_text("Only seller can do this")
        return

    cursor.execute("""
    UPDATE deals SET action_type=?
    WHERE id=?
    """, (action, deal_id))

    conn.commit()

    # ================= GROUP BUYER NOTIFICATION =================
    await update.message.reply_text(
        f"⚠️ ESCROW ACTION REQUEST ⚠️\n\n"
        f"🆔 Deal {format_deal_id(deal_id)}\n"
        f"👤 Seller: {seller}\n"
        f"👤 Buyer: {buyer}\n"
        f"📌 Action: {action.upper()}\n\n"
        f"👉 Buyer please respond below"
    )

    keyboard = [[
        InlineKeyboardButton("✅ Accept", callback_data=f"acc_{deal_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{deal_id}")
    ]]

    await update.message.reply_text(
        "Waiting buyer response...",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await seller_action(update, context, "release")


async def refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await seller_action(update, context, "refund")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await seller_action(update, context, "cancel")


# ================= BUYER BUTTONS =================
async def buyer_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    deal_id = int(data[1])

    cursor.execute("""
    SELECT buyer_username, action_type
    FROM deals WHERE id=?
    """, (deal_id,))

    deal = cursor.fetchone()

    if not deal:
        return

    buyer, action_type = deal
    user = (query.from_user.username or "").replace("@", "").lower()

    if user != buyer.lower():
        await query.answer("Not buyer", show_alert=True)
        return

    if action == "rej":
        await query.edit_message_text("❌ Buyer rejected request")
        return

    cursor.execute("""
    UPDATE deals SET buyer_confirmed=1, status=?
    WHERE id=?
    """, (f"{action_type.upper()}_CONFIRMED", deal_id))

    conn.commit()

    await query.edit_message_text(
        f"✅ Buyer confirmed {action_type.upper()}\n\nWaiting admin approval..."
    )


# ================= ADMIN =================
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("Admin only", show_alert=True)
        return

    data = query.data.split("_")
    action = data[1]
    deal_id = int(data[2])

    cursor.execute("""
    SELECT seller_username, buyer_username, amount, method, created_at
    FROM deals WHERE id=?
    """, (deal_id,))

    deal = cursor.fetchone()

    if not deal:
        return

    seller, buyer, amount, method, created_at = deal

    duration = format_duration(created_at)

    if action == "ok":
        cursor.execute("SELECT action_type FROM deals WHERE id=?", (deal_id,))
        row = cursor.fetchone()
        action_type = row[0] if row else "release"

        if action_type == "refund":
            status = "REFUNDED"
        elif action_type == "cancel":
            status = "CANCELLED"
        else:
            status = "COMPLETED"
    else:
        status = "CANCELLED"

    cursor.execute("""
    UPDATE deals SET handled_by=?
    WHERE id=?
    """, (f"@{query.from_user.username}", deal_id))
    conn.commit()

    text = (
        f"📢 FINAL RESULT\n\n"
        f"🆔 Deal ID: {format_deal_id(deal_id)}\n"
        f"👤 Seller: {seller}\n"
        f"👤 Buyer: {buyer}\n"
        f"💰 Amount: {amount}\n"
        f"💳 Method: {method}\n"
        f"⏱ Duration: {duration}\n"
        f"👮 Handled by: @{query.from_user.username}\n"
        f"📌 Status: {status}"
    )

    await query.edit_message_text(text)

    if PROOF_CHANNEL:
        await context.bot.send_message(PROOF_CHANNEL, text)


# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("activate", activate))

app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(CallbackQueryHandler(buyer_buttons, pattern="^(acc|rej)_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))

app.run_polling()
