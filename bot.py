import os
import sqlite3
import time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================
# ENV
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_username TEXT,
    buyer_username TEXT,
    seller_id INTEGER,
    buyer_id INTEGER,
    amount TEXT,
    method TEXT,
    status TEXT,
    handled_by TEXT,
    created_at REAL,
    completed_at REAL,
    deal_message_id INTEGER,
    chat_id INTEGER
)
""")

conn.commit()

# =========================
# HELPERS
# =========================

def is_admin(user_id):
    return user_id == ADMIN_ID


def format_duration(seconds):
    minutes = int(seconds // 60)
    hours = int(minutes // 60)

    if hours > 0:
        return f"{hours}h {minutes % 60}m"

    return f"{minutes}m"


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Escrow Bot v5 Running\n\n"
        "Create Deal:\n"
        "/deal @seller @buyer amount method\n\n"
        "Example:\n"
        "/deal @john @mike 300 Binance"
    )


# =========================
# CREATE DEAL
# =========================

async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:
        await update.message.reply_text(
            "❌ Usage:\n"
            "/deal @seller @buyer amount method"
        )
        return

    seller_username = context.args[0]
    buyer_username = context.args[1]
    amount = context.args[2]
    method = " ".join(context.args[3:])

    cursor.execute("""
    INSERT INTO deals (
        seller_username,
        buyer_username,
        amount,
        method,
        status,
        created_at,
        chat_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        seller_username,
        buyer_username,
        amount,
        method,
        "PENDING",
        time.time(),
        update.effective_chat.id
    ))

    conn.commit()

    deal_id = cursor.lastrowid

    msg = await update.message.reply_text(
        f"🆕 ESCROW REQUEST #{deal_id}\n\n"
        f"Seller: {seller_username}\n"
        f"Buyer: {buyer_username}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n\n"
        f"⏳ Waiting for admin activation..."
    )

    cursor.execute("""
    UPDATE deals
    SET deal_message_id=?
    WHERE id=?
    """, (
        msg.message_id,
        deal_id
    ))

    conn.commit()


# =========================
# ACTIVATE DEAL
# =========================

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Reply to a deal message"
        )
        return

    replied_message_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, amount, method
    FROM deals
    WHERE deal_message_id=?
    """, (replied_message_id,))

    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("❌ Deal not found")
        return

    deal_id, seller, buyer, amount, method = deal

    cursor.execute("""
    UPDATE deals
    SET status=?, handled_by=?
    WHERE id=?
    """, (
        "ACTIVE",
        update.effective_user.username or "admin",
        deal_id
    ))

    conn.commit()

    await update.message.reply_text(
        f"✅ DEAL ACTIVATED #{deal_id}\n\n"
        f"Seller: {seller}\n"
        f"Buyer: {buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n\n"
        f"Seller can now use:\n"
        f"/release\n"
        f"/refund\n"
        f"/cancel"
    )


# =========================
# SELLER ACTIONS
# =========================

async def seller_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action):

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Reply to activated deal"
        )
        return

    replied_message_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT
    id,
    seller_username,
    buyer_username,
    amount,
    method,
    status
    FROM deals
    WHERE deal_message_id=?
    """, (replied_message_id,))

    deal = cursor.fetchone()

    if not deal:
        await update.message.reply_text("❌ Deal not found")
        return

    deal_id, seller, buyer, amount, method, status = deal

    if status != "ACTIVE":
        await update.message.reply_text(
            "❌ Deal is not active"
        )
        return

    sender_username = f"@{update.effective_user.username}"

    if sender_username.lower() != seller.lower():
        await update.message.reply_text(
            "❌ Only seller can do this"
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Accept",
                callback_data=f"accept_{action}_{deal_id}"
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject_{action}_{deal_id}"
            )
        ]
    ]

    action_text = action.upper()

    await update.message.reply_text(
        f"⚠️ Seller requested: {action_text}\n\n"
        f"Buyer: {buyer}\n"
        f"Please confirm.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# RELEASE
# =========================

async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await seller_action(update, context, "release")


# =========================
# REFUND
# =========================

async def refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await seller_action(update, context, "refund")


# =========================
# CANCEL
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await seller_action(update, context, "cancel")


# =========================
# BUTTONS
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    parts = data.split("_")

    decision = parts[0]
    action = parts[1]
    deal_id = int(parts[2])

    cursor.execute("""
    SELECT
    seller_username,
    buyer_username,
    amount,
    method,
    handled_by,
    created_at
    FROM deals
    WHERE id=?
    """, (deal_id,))

    deal = cursor.fetchone()

    if not deal:
        await query.edit_message_text("❌ Deal not found")
        return

    seller, buyer, amount, method, handled_by, created_at = deal

    clicker = f"@{query.from_user.username}"

    # =========================
    # ONLY BUYER CAN CLICK
    # =========================

    if clicker.lower() != buyer.lower():
        await query.answer(
            "❌ You are not the buyer",
            show_alert=True
        )
        return

    # =========================
    # REJECT
    # =========================

    if decision == "reject":

        await query.edit_message_text(
            f"❌ Buyer rejected seller request."
        )

        return

    # =========================
    # ACCEPT
    # =========================

    completed_time = time.time()

    duration = format_duration(
        completed_time - created_at
    )

    status_text = ""

    if action == "release":
        status_text = "✅ DEAL COMPLETED"

        final_status = "COMPLETED"

    elif action in ["refund", "cancel"]:
        status_text = "⚠️ DEAL CANCELLED"

        final_status = "CANCELLED"

    else:
        return

    cursor.execute("""
    UPDATE deals
    SET status=?, completed_at=?
    WHERE id=?
    """, (
        final_status,
        completed_time,
        deal_id
    ))

    conn.commit()

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Admin Confirm",
                callback_data=f"adminconfirm_{deal_id}"
            )
        ]
    ]

    await query.edit_message_text(
        f"{status_text}\n\n"
        f"Waiting for admin confirmation...",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ADMIN CONFIRM
# =========================

async def admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    if not data.startswith("adminconfirm_"):
        return

    if not is_admin(query.from_user.id):
        await query.answer(
            "❌ Admin only",
            show_alert=True
        )
        return

    deal_id = int(data.split("_")[1])

    cursor.execute("""
    SELECT
    seller_username,
    buyer_username,
    amount,
    method,
    handled_by,
    status,
    created_at,
    completed_at
    FROM deals
    WHERE id=?
    """, (deal_id,))

    deal = cursor.fetchone()

    if not deal:
        return

    (
        seller,
        buyer,
        amount,
        method,
        handled_by,
        status,
        created_at,
        completed_at
    ) = deal

    duration = format_duration(
        completed_at - created_at
    )

    if status == "COMPLETED":
        final_text = (
            f"✅ DEAL COMPLETED\n\n"
        )
    else:
        final_text = (
            f"⚠️ DEAL CANCELLED\n\n"
        )

    final_text += (
        f"Seller: {seller}\n"
        f"Buyer: {buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n"
        f"Handled by: @{handled_by}\n\n"
        f"⏱ Duration: {duration}\n\n"
        f"Status: {status}"
    )

    await query.edit_message_text(final_text)

    if PROOF_CHANNEL:
        await context.bot.send_message(
            chat_id=PROOF_CHANNEL,
            text=final_text
        )


# =========================
# MAIN
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("activate", activate))
app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(
    CallbackQueryHandler(
        admin_confirm,
        pattern="^adminconfirm_"
    )
)

app.add_handler(
    CallbackQueryHandler(buttons)
)

print("🚀 Escrow Bot v5 Running...")

app.run_polling()
