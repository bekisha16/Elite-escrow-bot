import os
import sqlite3
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

ADMIN_IDS = [6138132255, 5635739078]

# ================= DB =================
conn = sqlite3.connect("escrow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller TEXT,
    buyer TEXT,
    amount TEXT,
    method TEXT,
    status TEXT,
    action TEXT,
    msg_id INTEGER,
    created REAL,
    handled_by TEXT
)
""")

conn.commit()

# ================= HELPERS =================
def deal_id(i):
    return f"#{i:03d}"

def clean(u):
    return (u or "").replace("@", "").strip().lower()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escrow Bot Running ✅")

# ================= DEAL =================
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:
        return await update.message.reply_text("Usage: /deal @seller @buyer amount method")

    seller = clean(context.args[0])
    buyer = clean(context.args[1])
    amount = context.args[2]
    method = " ".join(context.args[3:])

    cursor.execute("""
    INSERT INTO deals (seller, buyer, amount, method, status, created)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (seller, buyer, amount, method, "PENDING", time.time()))

    conn.commit()

    did = cursor.lastrowid

    msg = await update.message.reply_text(
        f"NEW DEAL {deal_id(did)}\n"
        f"Seller: @{seller}\n"
        f"Buyer: @{buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}"
    )

    cursor.execute("UPDATE deals SET msg_id=? WHERE id=?", (msg.message_id, did))
    conn.commit()

# ================= ACTIVATE =================
async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Admin only")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to deal")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("SELECT id FROM deals WHERE msg_id=?", (msg_id,))
    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("Not found")

    did = row[0]

    cursor.execute("UPDATE deals SET status=? WHERE id=?", ("ACTIVE", did))
    conn.commit()

    await update.message.reply_text(f"Activated {deal_id(did)}")

# ================= ACTION =================
async def seller_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action):

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply required")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("SELECT id, seller, status FROM deals WHERE msg_id=?", (msg_id,))
    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("Not found")

    did, seller, status = row

    if status != "ACTIVE":
        return await update.message.reply_text("Not active")

    sender = clean(update.effective_user.username)

    if sender != seller:
        return await update.message.reply_text("Only seller")

    cursor.execute("UPDATE deals SET action=? WHERE id=?", (action, did))
    conn.commit()

    kb = [[
        InlineKeyboardButton("Accept", callback_data=f"acc_{did}"),
        InlineKeyboardButton("Reject", callback_data=f"rej_{did}")
    ]]

    await update.message.reply_text(
        f"Request: {action}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def release(update, context):
    await seller_action(update, context, "release")

async def refund(update, context):
    await seller_action(update, context, "refund")

async def cancel(update, context):
    await seller_action(update, context, "cancel")

# ================= BUYER =================
async def buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    action, did = q.data.split("_")
    did = int(did)

    cursor.execute("SELECT buyer, action FROM deals WHERE id=?", (did,))
    row = cursor.fetchone()

    if not row:
        return

    buyer, act = row

    if clean(q.from_user.username) != buyer:
        return await q.answer("Not buyer", show_alert=True)

    if action == "rej":
        return await q.edit_message_text("Rejected")

    cursor.execute("UPDATE deals SET status=? WHERE id=?", (act.upper() + "_CONFIRMED", did))
    conn.commit()

    await q.edit_message_text("Buyer confirmed")

# ================= LEADERBOARD (FIXED) =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return

    cursor.execute("SELECT handled_by, status FROM deals WHERE handled_by IS NOT NULL")
    rows = cursor.fetchall()

    stats = {}

    for admin, status in rows:

        name = admin if admin else "Unknown"

        if name not in stats:
            stats[name] = {"t": 0, "c": 0, "r": 0, "x": 0}

        stats[name]["t"] += 1

        if status == "COMPLETED":
            stats[name]["c"] += 1
        elif status == "REFUNDED":
            stats[name]["r"] += 1
        elif status == "CANCELLED":
            stats[name]["x"] += 1

    text = "🏆 LEADERBOARD\n\n"

    i = 1
    for admin, d in sorted(stats.items(), key=lambda x: x[1]["t"], reverse=True):
        text += (
            f"{i}. @{admin}\n"
            f"Total: {d['t']}\n"
            f"Completed: {d['c']}\n"
            f"Refunded: {d['r']}\n"
            f"Cancelled: {d['x']}\n\n"
        )
        i += 1

    await update.message.reply_text(text)

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("activate", activate))

app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CallbackQueryHandler(buyer, pattern="^(acc|rej)_"))

app.run_polling()       stats[admin]["completed"] += 1
        elif status == "REFUNDED":
            stats[admin]["refunded"] += 1
        elif status == "CANCELLED":
            stats[admin]["cancelled"] += 1

    sorted_admins = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)

    text = "🏆 ADMIN LEADERBOARD\n\n"

    rank = 1
    for admin, data in sorted_admins:
        text += (
            f"{rank}. {admin}\n"
            f"📦 Total: {data['total']}\n"
            f"✅ Completed: {data['completed']}\n"
            f"💸 Refunded: {data['refunded']}\n"
            f"❌ Cancelled: {data['cancelled']}\n\n"
        )
        rank += 1

    await update.message.reply_text(text)

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("activate", activate))

app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("history", history))
app.add_handler(CommandHandler("leaderboard", leaderboard))

app.add_handler(CallbackQueryHandler(buyer_buttons, pattern="^(acc|rej)_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))

app.run_polling()
