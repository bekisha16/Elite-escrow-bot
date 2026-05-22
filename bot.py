import os
import sqlite3
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

# Put ALL admin IDs here (safe list system)
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
    activator_admin_id INTEGER
)
""")

conn.commit()

# ================= HELPERS =================
def deal_id(did):
    return f"#{did:03d}"

def admin_tag(user):
    """Always safe admin format"""
    if user.username:
        return f"@{user.username}"
    return f"id:{user.id}"

def clean_username(u):
    return (u or "").replace("@", "").strip().lower()

def duration(start):
    s = int(time.time() - start)
    m = s // 60
    h = m // 60
    m = m % 60
    return f"{h}h {m}m" if h else f"{m}m"

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escrow Bot Running ✅")

# ================= DEAL =================
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:
        return await update.message.reply_text("Usage: /deal @seller @buyer amount method")

    seller = clean_username(context.args[0])
    buyer = clean_username(context.args[1])
    amount = context.args[2]
    method = " ".join(context.args[3:])

    cursor.execute("""
    INSERT INTO deals (seller_username, buyer_username, amount, method, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (seller, buyer, amount, method, "PENDING", time.time()))

    conn.commit()

    did = cursor.lastrowid

    msg = await update.message.reply_text(
        f"🚨 NEW DEAL {deal_id(did)}\n"
        f"Seller: @{seller}\n"
        f"Buyer: @{buyer}\n"
        f"Amount: {amount}\n"
        f"Method: {method}\n\n"
        f"Waiting activation..."
    )

    cursor.execute("UPDATE deals SET deal_message_id=? WHERE id=?", (msg.message_id, did))
    conn.commit()

# ================= ACTIVATE =================
async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("❌ Admin only")

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to deal")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, amount, method
    FROM deals WHERE deal_message_id=?
    """, (msg_id,))

    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("Deal not found")

    did, seller, buyer, amount, method = row

    cursor.execute("""
    UPDATE deals
    SET status=?, activator_admin_id=?
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

# ================= SELLER ACTION =================
async def seller_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action):

    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to deal")

    msg_id = update.message.reply_to_message.message_id

    cursor.execute("""
    SELECT id, seller_username, buyer_username, status
    FROM deals WHERE deal_message_id=?
    """, (msg_id,))

    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("Deal not found")

    did, seller, buyer, status = row

    if status != "ACTIVE":
        return await update.message.reply_text("Deal not active")

    sender = clean_username(update.effective_user.username)

    if sender != seller:
        return await update.message.reply_text("Only seller can do this")

    cursor.execute("""
    UPDATE deals SET action_type=? WHERE id=?
    """, (action, did))

    conn.commit()

    keyboard = [[
        InlineKeyboardButton("✅ Accept", callback_data=f"acc_{did}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{did}")
    ]]

    await update.message.reply_text(
        f"⚠ Seller requested: {action.upper()}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def release(update, context):
    await seller_action(update, context, "release")

async def refund(update, context):
    await seller_action(update, context, "refund")

async def cancel(update, context):
    await seller_action(update, context, "cancel")

# ================= BUYER =================
async def buyer_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    action, did = q.data.split("_")
    did = int(did)

    cursor.execute("""
    SELECT buyer_username, action_type
    FROM deals WHERE id=?
    """, (did,))

    row = cursor.fetchone()

    if not row:
        return

    buyer, action_type = row

    buyer = clean_username(buyer)
    user = clean_username(q.from_user.username)

    if user != buyer:
        return await q.answer("Not buyer", show_alert=True)

    if action == "rej":
        return await q.edit_message_text("❌ Rejected")

    cursor.execute("""
    UPDATE deals SET buyer_confirmed=1, status=?
    WHERE id=?
    """, (f"{action_type.upper()}_CONFIRMED", did))

    conn.commit()

    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"adm_ok_{did}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"adm_no_{did}")
    ]]

    await q.edit_message_text("Buyer confirmed. Waiting admin...")

    await context.bot.send_message(
        chat_id=q.message.chat_id,
        text=f"📌 Admin review needed for {deal_id(did)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= ADMIN =================
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    parts = q.data.split("_")

    if len(parts) != 3:
        return

    _, status, did = parts
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
        if action_type == "refund":
            final = "REFUNDED"
        elif action_type == "cancel":
            final = "CANCELLED"
        else:
            final = "COMPLETED"
    else:
        final = "CANCELLED"

    cursor.execute("""
    UPDATE deals SET status=?, handled_by=? WHERE id=?
    """, (final, admin_tag(q.from_user), did))

    conn.commit()

    text = (
        f"📢 FINAL RESULT\n\n"
        f"🆔 Deal ID: {deal_id(did)}\n"
        f"👤 Seller: @{seller}\n"
        f"👤 Buyer: @{buyer}\n"
        f"💰 Amount: {amount}\n"
        f"💳 Method: {method}\n"
        f"⏱ Duration: {duration(created)}\n"
        f"👮 Handled by: {admin_tag(q.from_user)}\n"
        f"📌 Status: {final}"
    )

    await q.edit_message_text(text)

# ================= STATUS =================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    admin = admin_tag(update.effective_user)

    cursor.execute("""
    SELECT status FROM deals WHERE handled_by=?
    """, (admin,))

    rows = cursor.fetchall()

    if not rows:
        return await update.message.reply_text("No deals handled by you")

    total = len(rows)

    completed = sum(1 for r in rows if r[0] == "COMPLETED")
    refunded = sum(1 for r in rows if r[0] == "REFUNDED")
    cancelled = sum(1 for r in rows if r[0] == "CANCELLED")

    await update.message.reply_text(
        f"👤 YOUR STATUS\n\n"
        f"Total: {total}\n"
        f"Completed: {completed}\n"
        f"Refunded: {refunded}\n"
        f"Cancelled: {cancelled}\n"
    )

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("❌ Admin only")

    cursor.execute("""
    SELECT handled_by, status FROM deals WHERE handled_by IS NOT NULL
    """)
    rows = cursor.fetchall()

    stats = {}

    for admin, status in rows:

        admin = admin.strip()

        if admin not in stats:
            stats[admin] = {
                "total": 0,
                "completed": 0,
                "refunded": 0,
                "cancelled": 0
            }

        stats[admin]["total"] += 1

        if status == "COMPLETED":
            stats[admin]["completed"] += 1
        elif status == "REFUNDED":
            stats[admin]["refunded"] += 1
        elif status == "CANCELLED":
            stats[admin]["cancelled"] += 1

    sorted_admins = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)

    text = "🏆 ADMIN LEADERBOARD\n\n"

    rank = 1
    for admin, d in sorted_admins:
        text += (
            f"{rank}. {admin}\n"
            f"📦 Total: {d['total']}\n"
            f"✅ Completed: {d['completed']}\n"
            f"💸 Refunded: {d['refunded']}\n"
            f"❌ Cancelled: {d['cancelled']}\n\n"
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

app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("leaderboard", leaderboard))

app.add_handler(CallbackQueryHandler(buyer_buttons, pattern="^(acc|rej)_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))

app.run_polling()("SELECT handled_by, status FROM deals WHERE handled_by IS NOT NULL")
    rows = cursor.fetchall()

    stats = {}

    for admin, status in rows:

        admin = admin.strip()

        if admin not in stats:
            stats[admin] = {
                "total": 0,
                "completed": 0,
                "refunded": 0,
                "cancelled": 0
            }

        stats[admin]["total"] += 1

        if status == "COMPLETED":
            stats[admin]["completed"] += 1
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
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("leaderboard", leaderboard))

app.add_handler(CallbackQueryHandler(buyer_buttons, pattern="^(acc|rej)_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))

app.run_polling()IDS:
        return

    cursor.execute("SELECT handled_by, status FROM deals WHERE handled_by IS NOT NULL")
    rows = cursor.fetchall()

    stats = {}

    for admin, status in rows:

        admin = admin.strip()

        if admin not in stats:
            stats[admin] = {
                "total": 0,
                "completed": 0,
                "refunded": 0,
                "cancelled": 0
            }

        stats[admin]["total"] += 1

        if status == "COMPLETED":
            stats[admin]["completed"] += 1
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
