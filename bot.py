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

import os
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- ENV ----------------
TOKEN = os.getenv("BOT_TOKEN")
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")

# MULTI ADMIN SUPPORT
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


# ---------------- DB ----------------
conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer INTEGER,
    seller INTEGER,
    amount TEXT,
    status TEXT,
    created_at REAL
)
""")
conn.commit()


# ---------------- CHECK ADMIN ----------------
def is_admin(user_id: int):
    return user_id in ADMIN_IDS


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
import os
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- ENV ----------------
TOKEN = os.getenv("BOT_TOKEN")
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")

ADMIN_IDS = [
    int(x)
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
]

# ---------------- DB ----------------
conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer INTEGER,
    seller INTEGER,
    amount TEXT,
    status TEXT,
    created_at REAL
)
""")
conn.commit()

# ---------------- ADMIN CHECK ----------------
def is_admin(user_id: int):
    return user_id in ADMIN_IDS


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Escrow Bot v4 Ready\n\n"
        "Commands:\n"
        "/deal <amount>\n"
        "/release <id>\n"
        "/cancel <id>"
    )


# ---------------- DEAL ----------------
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /deal <amount>")
        return

    amount = context.args[0]
    buyer = update.effective_user.id

    cursor.execute(
        "INSERT INTO deals (buyer, seller, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (buyer, None, amount, "PENDING", time.time())
    )
    conn.commit()

    deal_id = cursor.lastrowid

    keyboard = [
        [InlineKeyboardButton("🤝 Request Release", callback_data=f"req_release_{deal_id}")],
        [InlineKeyboardButton("❌ Request Cancel", callback_data=f"req_cancel_{deal_id}")]
    ]

    await update.message.reply_text(
        f"💰 DEAL #{deal_id}\n💵 Amount: {amount}\n📌 Status: PENDING",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- BUTTONS ----------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    try:
        deal_id = int(data.split("_")[-1])
    except:
        await query.answer("Error", show_alert=True)
        return

    cursor.execute("SELECT buyer, seller, amount FROM deals WHERE id=?", (deal_id,))
    deal = cursor.fetchone()

    if not deal:
        await query.edit_message_text("❌ Deal not found")
        return

    buyer, seller, amount = deal


    # ---------------- REQUEST RELEASE ----------------
    if data.startswith("req_release_"):

        keyboard = [
            [InlineKeyboardButton("✅ Approve Release", callback_data=f"appr_release_{deal_id}")],
            [InlineKeyboardButton("❌ Approve Cancel", callback_data=f"appr_cancel_{deal_id}")]
        ]

        await query.edit_message_text(
            f"📦 DEAL #{deal_id}\n💵 {amount}\n⏳ RELEASE REQUESTED",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ---------------- REQUEST CANCEL ----------------
    elif data.startswith("req_cancel_"):

        keyboard = [
            [InlineKeyboardButton("❌ Approve Cancel", callback_data=f"appr_cancel_{deal_id}")],
            [InlineKeyboardButton("🔄 Reject", callback_data=f"reject_{deal_id}")]
        ]

        await query.edit_message_text(
            f"📦 DEAL #{deal_id}\n💵 {amount}\n⚠️ CANCEL REQUESTED",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ---------------- APPROVE RELEASE ----------------
    elif data.startswith("appr_release_"):

        if not is_admin(query.from_user.id):
            await query.answer("❌ Admin only", show_alert=True)
            return

        cursor.execute("UPDATE deals SET status=? WHERE id=?", ("COMPLETED", deal_id))
        conn.commit()

        msg = f"💸 ESCROW COMPLETED\nDEAL #{deal_id}\n💵 {amount}"

        await query.edit_message_text(msg)

        if PROOF_CHANNEL:
            await context.bot.send_message(chat_id=PROOF_CHANNEL, text=msg)


    # ---------------- APPROVE CANCEL ----------------
    elif data.startswith("appr_cancel_"):

        if not is_admin(query.from_user.id):
            await query.answer("❌ Admin only", show_alert=True)
            return

      import os
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- ENV ----------------
TOKEN = os.getenv("BOT_TOKEN")
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")

ADMIN_IDS = [
    int(x)
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
]

# ---------------- DB ----------------
conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer INTEGER,
    seller INTEGER,
    amount TEXT,
    status TEXT,
    created_at REAL
)
""")
conn.commit()

# ---------------- ADMIN CHECK ----------------
def is_admin(user_id: int):
    return user_id in ADMIN_IDS


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Escrow Bot v4 Fixed\n\n"
        "Commands:\n"
        "/deal <amount>\n"
        "/release <id>\n"
        "/cancel <id>"
    )


# ---------------- DEAL (FIXED /deal 400 ISSUE) ----------------
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ Usage: /deal <amount>\nExample: /deal 400")
            return

        amount = " ".join(context.args).strip()
        if not amount:
            await update.message.reply_text("❌ Invalid amount")
            return

        buyer = update.effective_user.id

        cursor.execute(
            "INSERT INTO deals (buyer, seller, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (buyer, None, amount, "PENDING", time.time())
        )
        conn.commit()

        deal_id = cursor.lastrowid

        keyboard = [
            [InlineKeyboardButton("🤝 Request Release", callback_data=f"req_release_{deal_id}")],
            [InlineKeyboardButton("❌ Request Cancel", callback_data=f"req_cancel_{deal_id}")]
        ]

        await update.message.reply_text(
            f"💰 DEAL #{deal_id}\n💵 Amount: {amount}\n📌 Status: PENDING",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")


# ---------------- BUTTON HANDLER ----------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    try:
        deal_id = int(data.split("_")[-1])
    except:
        await query.answer("Error", show_alert=True)
        return

    cursor.execute("SELECT buyer, seller, amount FROM deals WHERE id=?", (deal_id,))
    deal = cursor.fetchone()

    if not deal:
        await query.edit_message_text("❌ Deal not found")
        return

    buyer, seller, amount = deal


    # ---------------- REQUEST RELEASE ----------------
    if data.startswith("req_release_"):

        keyboard = [
            [InlineKeyboardButton("✅ Approve Release", callback_data=f"appr_release_{deal_id}")],
            [InlineKeyboardButton("❌ Approve Cancel", callback_data=f"appr_cancel_{deal_id}")]
        ]

        await query.edit_message_text(
            f"📦 DEAL #{deal_id}\n💵 {amount}\n⏳ RELEASE REQUESTED",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ---------------- REQUEST CANCEL ----------------
    elif data.startswith("req_cancel_"):

        keyboard = [
            [InlineKeyboardButton("❌ Approve Cancel", callback_data=f"appr_cancel_{deal_id}")],
            [InlineKeyboardButton("🔄 Reject", callback_data=f"reject_{deal_id}")]
        ]

        await query.edit_message_text(
            f"📦 DEAL #{deal_id}\n💵 {amount}\n⚠️ CANCEL REQUESTED",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ---------------- APPROVE RELEASE ----------------
    elif data.startswith("appr_release_"):

        if not is_admin(query.from_user.id):
            await query.answer("❌ Admin only", show_alert=True)
            return

        cursor.execute("UPDATE deals SET status=? WHERE id=?", ("COMPLETED", deal_id))
        conn.commit()

        msg = f"💸 ESCROW COMPLETED\nDEAL #{deal_id}\n💵 {amount}"

        await query.edit_message_text(msg)

        if PROOF_CHANNEL:
            await context.bot.send_message(chat_id=PROOF_CHANNEL, text=msg)


    # ---------------- APPROVE CANCEL ----------------
    elif data.startswith("appr_cancel_"):

        if not is_admin(query.from_user.id):
            await query.answer("❌ Admin only", show_alert=True)
            return

        cursor.execute("UPDATE deals SET status=? WHERE id=?", ("CANCELLED", deal_id))
        conn.commit()

        msg = f"⚠️ ESCROW CANCELLED\nDEAL #{deal_id}\n💵 {amount}"

        await query.edit_message_text(msg)

        if PROOF_CHANNEL:
            await context.bot.send_message(chat_id=PROOF_CHANNEL, text=msg)


    # ---------------- REJECT ----------------
    elif data.startswith("reject_"):
        if is_admin(query.from_user.id):
            await query.edit_message_text("❌ Request rejected")
        else:
            await query.answer("❌ Not allowed", show_alert=True)


# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CallbackQueryHandler(buttons))

print("🚀 Escrow Bot v4 FIXED Running...")

app.run_polling()
