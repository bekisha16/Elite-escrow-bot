from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime
import os

# =========================
# BOT CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("BOT_TOKEN missing")
    exit()

PROOF_CHANNEL = "@eliteescrowproof"

ADMINS = [
    8216037421,
    5635739078,
    7986300943,
    6632452285,
    6953440368
]

deal_id = 0


def is_admin(user_id):
    return user_id in ADMINS


# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Escrow Bot Online")


# =========================
# DEAL COMMAND
# =========================

async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global deal_id

    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Not allowed")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n/deal @buyer @seller amount details"
        )

    deal_id += 1

    buyer = context.args[0]
    seller = context.args[1]
    amount = context.args[2]
    details = " ".join(context.args[3:])

    username = update.effective_user.username

    if username is None:
        username = "unknown"

    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"""
━━━━━━━━━━━━━━
💼 ESCROW PROOF

🆔 Deal ID: #{deal_id:04d}

👤 Buyer: {buyer}
👤 Seller: {seller}

💰 Amount: {amount}
📝 Details: {details}

🛡 Handled By: @{username}

📅 {time}

✅ COMPLETED
━━━━━━━━━━━━━━
"""

    await context.bot.send_message(PROOF_CHANNEL, message)

    await update.message.reply_text(
        f"✅ Deal posted successfully #{deal_id:04d}"
    )


# =========================
# BOT START
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))

print("✅ Escrow Bot Running")

app.run_polling()
