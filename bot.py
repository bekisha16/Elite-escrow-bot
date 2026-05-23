import os
import sqlite3
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

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
    return (u or "").replace("@", "").strip().lower()

def clean_field(v):
    return (v or "").strip()

def safe_user(user):
    return (user.username or str(user.id)).lower()

def deal_id(did):
    return f"#{did:03d}"

def duration(start):
    s = int(time.time() - start)
    m = s // 60
    h = m // 60
    m = m % 60
    return f"{h}h {m}m" if h else f"{m}m"

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escrow Bot Running ✅")

# ================= FORM =================
async def deal_form(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if "buyer:" not in text.lower() or "seller:" not in text.lower():
        return

    try:
        lines = text.split("\n")
        data = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().lower()] = value.strip()

        seller = clean_username(data.get("seller"))
        buyer = clean_username(data.get("buyer"))
        amount = clean_field(data.get("amount"))
        method = clean_field(data.get("method"))

        if not seller or not buyer or not amount or not method:
            return await update.message.reply_text("❌ Invalid escrow form")

        cursor.execute("""
        INSERT INTO deals (seller_username, buyer_username, amount, method, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (seller, buyer, amount, method, "PENDING", time.time()))

        conn.commit()

        did = cursor.lastrowid

        msg = await update.message.reply_text(
            f"🚨 NEW DEAL {deal_id(did)}\n\n"
            f"Seller: @{seller}\n"
            f"Buyer: @{buyer}\n"
            f"Amount: {amount}\n"
            f"Method: {method}\n\n"
            f"⏳ Waiting admin activation..."
        )

        cursor.execute("UPDATE deals SET deal_message_id=? WHERE id=?", (msg.message_id, did))
        conn.commit()

    except Exception as e:
        logger.error(f"Form error: {e}")
        await update.message.reply_text("❌ Error processing form")

# ================= ACTIVATE =================
async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("❌ Admin only")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to deal")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, amount, method, created_at
    FROM deals WHERE deal_message_id=?
    """, (msg_id,))

    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("Deal not found")

    did, seller, buyer, amount, method, created = row

    cursor.execute("""
    UPDATE deals SET status=?, activator_admin_id=?
    WHERE id=?
    """, ("ACTIVE", update.effective_user.id, did))

    conn.commit()

    await update.message.reply_text(
        f"✅ DEAL ACTIVATED {deal_id(did)}\n"
        f"Seller: @{seller}\n"
        f"Buyer: @{buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}"
    )

# ================= SELLER ACTION (FIXED MESSAGE) =================
async def seller_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action):

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to deal")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, status, action_locked
    FROM deals WHERE deal_message_id=?
    """, (msg_id,))

    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("Not found")

    did, seller, buyer, status, locked = row

    if status != "ACTIVE":
        return await update.message.reply_text("Not active")

    if locked == 1:
        return await update.message.reply_text("Already processed")

    sender = clean_username(safe_user(update.effective_user))

    if sender != seller:
        return await update.message.reply_text("Only seller can do this")

    cursor.execute("""
    UPDATE deals SET action_type=?, action_locked=1 WHERE id=?
    """, (action, did))

    conn.commit()

    keyboard = [[
        InlineKeyboardButton("✔ Accept", callback_data=f"acc_{did}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{did}")
    ]]

    # ✅ YOUR REQUESTED MESSAGE
    await update.message.reply_text(
        f"⚠ SELLER REQUEST\n\n"
        f"🆔 Deal: {deal_id(did)}\n"
        f"👤 Seller: @{seller}\n"
        f"👤 Buyer: @{buyer}\n\n"
        f"📌 Seller requested for deal {action}\n"
        f"👉 Buyer pls accept or release/cancel/refund\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def release(update, context):
    await seller_action(update, context, "release")

async def refund(update, context):
    await seller_action(update, context, "refund")

async def cancel(update, context):
    await seller_action(update, context, "cancel")

# ================= ADMIN =================
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    _, status, did = q.data.split("_")
    did = int(did)

    cursor.execute("""
    SELECT activator_admin_id, seller_username, buyer_username, amount, method, created_at, action_type
    FROM deals WHERE id=?
    """, (did,))

    row = cursor.fetchone()

    if not row:
        return

    admin_id, seller, buyer, amount, method, created, action_type = row

    if q.from_user.id != admin_id:
        return await q.answer("Only activating admin", show_alert=True)

    if status == "ok":
        final = (
            "REFUNDED" if action_type == "refund"
            else "CANCELLED" if action_type == "cancel"
            else "COMPLETED"
        )
    else:
        final = "CANCELLED"

    cursor.execute("""
    UPDATE deals SET status=?, handled_by=? WHERE id=?
    """, (final, safe_user(q.from_user), did))

    conn.commit()

    text = (
        f"📢 FINAL RESULT\n\n"
        f"🆔 Deal ID: {deal_id(did)}\n"
        f"👤 Seller: @{seller}\n"
        f"👤 Buyer: @{buyer}\n"
        f"💰 Amount: {amount}\n"
        f"💳 Method: {method}\n"
        f"⏱ Duration: {duration(created)}\n"
        f"👮 Handled by: @{safe_user(q.from_user)}\n"
        f"📌 Status: {final}"
    )

    await q.edit_message_text(text)

    # ================= PROOF CHANNEL FIXED =================
    if PROOF_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=str(PROOF_CHANNEL),
                text=text
            )
            logger.info("Proof sent successfully")
        except Exception as e:
            logger.error(f"Proof channel error: {e}")

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("activate", activate))

app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deal_form))

app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))
app.add_handler(CallbackQueryHandler(lambda u, c: None, pattern="^(acc|rej)_"))

app.run_polling()
