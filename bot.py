from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= HANDLER (DEBUG / TEST REPLY) =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text or text.startswith("/"):
        return

    await update.message.reply_text(f"Got it: {text}")


# ================= PROOF CHANNEL =================
# (keep your existing PROOF_CHANNEL variable above)
async def send_to_proof_channel(context, text):
    if PROOF_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=str(PROOF_CHANNEL),
                text=text
            )
        except Exception as e:
            logger.error(e)


# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return

    cursor.execute("SELECT status FROM deals")
    rows = cursor.fetchall()

    await update.message.reply_text(
        f"📊 ESCROW STATS\n\n"
        f"Total: {len(rows)}\n"
        f"Completed: {sum(1 for r in rows if r[0]=='COMPLETED')}\n"
        f"Refunded: {sum(1 for r in rows if r[0]=='REFUNDED')}\n"
        f"Cancelled: {sum(1 for r in rows if r[0]=='CANCELLED')}\n"
        f"Active: {sum(1 for r in rows if r[0]=='ACTIVE')}"
    )


# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return

    cursor.execute("""
    SELECT handled_by, status
    FROM deals
    WHERE handled_by IS NOT NULL
    """)

    rows = cursor.fetchall()

    stats = {}

    for admin, status in rows:

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

    sorted_admins = sorted(
        stats.items(),
        key=lambda x: x[1]["total"],
        reverse=True
    )

    text = "🏆 ADMIN LEADERBOARD\n\n"

    rank = 1

    for admin, data in sorted_admins:

        text += (
            f"{rank}. @{admin}\n"
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
app.add_handler(CommandHandler("activate", activate))
app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("refund", refund))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("leaderboard", leaderboard))

# 🔥 ESCROW CORE HANDLER (IMPORTANT)
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        deal_form
    )
)

# 🔥 GENERAL REPLY HANDLER (SAFE)
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handler
    )
)

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
