from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# ---------------- ENV VARIABLES ----------------
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PROOF_CHANNEL = os.getenv("PROOF_CHANNEL", "")

# ---------------- STORAGE (v1 simple memory) ----------------
deals = {}
deal_counter = 1


# ---------------- PROOF LOGGER ----------------
async def log_to_channel(context, text):
    if PROOF_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=PROOF_CHANNEL,
                text=text
            )
        except Exception as e:
            print("Channel log error:", e)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Elite Escrow Bot\n\n"
        "Commands:\n"
        "/deal <amount> - create deal\n"
        "/accept <id> - accept deal\n"
        "/status <id> - check deal\n"
        "/release <id> - admin release\n"
        "/cancel <id> - cancel deal"
    )


# ---------------- CREATE DEAL ----------------
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global deal_counter

    if not context.args:
        await update.message.reply_text("Usage: /deal <amount>")
        return

    amount = context.args[0]
    deal_id = deal_counter
    deal_counter += 1

    deals[deal_id] = {
        "amount": amount,
        "buyer": update.effective_user.id,
        "seller": None,
        "status": "PENDING"
    }

    msg = (
        f"💰 NEW DEAL CREATED\n"
        f"🆔 ID: {deal_id}\n"
        f"💵 Amount: {amount}\n"
        f"👤 Buyer: {update.effective_user.id}\n"
        f"📌 Status: PENDING"
    )

    await update.message.reply_text(msg)
    await log_to_channel(context, msg)


# ---------------- ACCEPT DEAL ----------------
async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /accept <deal_id>")
        return

    deal_id = int(context.args[0])

    if deal_id not in deals:
        await update.message.reply_text("❌ Deal not found")
        return

    deals[deal_id]["seller"] = update.effective_user.id
    deals[deal_id]["status"] = "ACTIVE"

    msg = (
        f"🤝 DEAL ACCEPTED\n"
        f"🆔 ID: {deal_id}\n"
        f"👤 Seller: {update.effective_user.id}\n"
        f"📌 Status: ACTIVE"
    )

    await update.message.reply_text(msg)
    await log_to_channel(context, msg)


# ---------------- STATUS ----------------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /status <deal_id>")
        return

    deal_id = int(context.args[0])

    if deal_id not in deals:
        await update.message.reply_text("❌ Deal not found")
        return

    d = deals[deal_id]

    await update.message.reply_text(
        f"📦 DEAL INFO\n"
        f"🆔 ID: {deal_id}\n"
        f"💵 Amount: {d['amount']}\n"
        f"👤 Buyer: {d['buyer']}\n"
        f"👤 Seller: {d['seller']}\n"
        f"📌 Status: {d['status']}"
    )


# ---------------- RELEASE (ADMIN ONLY) ----------------
async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can release deals")
        return

    if not context.args:
        await update.message.reply_text("Usage: /release <deal_id>")
        return

    deal_id = int(context.args[0])

    if deal_id not in deals:
        await update.message.reply_text("❌ Deal not found")
        return

    deals[deal_id]["status"] = "COMPLETED"

    msg = (
        f"💸 DEAL RELEASED\n"
        f"🆔 ID: {deal_id}\n"
        f"📌 Status: COMPLETED"
    )

    await update.message.reply_text(msg)
    await log_to_channel(context, msg)


# ---------------- CANCEL ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /cancel <deal_id>")
        return

    deal_id = int(context.args[0])

    if deal_id not in deals:
        await update.message.reply_text("❌ Deal not found")
        return

    user_id = update.effective_user.id
    d = deals[deal_id]

    if user_id != d["buyer"] and user_id != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    d["status"] = "CANCELLED"

    msg = f"⚠️ DEAL CANCELLED\n🆔 ID: {deal_id}"

    await update.message.reply_text(msg)
    await log_to_channel(context, msg)


# ---------------- MAIN ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deal", deal))
app.add_handler(CommandHandler("accept", accept))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("release", release))
app.add_handler(CommandHandler("cancel", cancel))

print("🚀 Elite Escrow Bot Running...")

app.run_polling()
