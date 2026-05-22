async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("❌ Admin only")

    cursor.execute("SELECT handled_by, status FROM deals WHERE handled_by IS NOT NULL")
    rows = cursor.fetchall()

    if not rows:
        return await update.message.reply_text("No admin activity yet")

    stats = {}

    for admin, status in rows:

        if not admin:
            continue

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

    await update.message.reply_text(text)CommandHandler("leaderboard", leaderboard))

    app.add_handler(CallbackQueryHandler(buyer_buttons, pattern="^(acc|rej)_"))
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()add_handler(CommandHandler("leaderboard", leaderboard))

    app.add_handler(CallbackQueryHandler(buyer_buttons, pattern="^(acc|rej)_"))
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^adm_"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()           f"💸 Refunded: {d['refunded']}\n"
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
