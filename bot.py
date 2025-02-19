from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

# ✅ Store user data
user_quiz_data = {}
WAITING_FOR_TITLE = 1  # State to wait for title input

async def collect_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_quiz_data:
        user_quiz_data[user_id] = {"quizzes": [], "waiting_for_title": False}

    if user_quiz_data[user_id]["waiting_for_title"]:
        await update.message.reply_text("⚠ पहले /done भेजें ताकि टाइटल माँगा जा सके।")
        return

    lines = text.split("\n")
    title = None
    link = None

    for line in lines:
        if "by @" in line:
            title = line.split(" by @")[0].strip()  # Extract title
        elif "t.me/QuizBot?start=" in line:
            link = line.strip()  # Extract link

        if title and link:
            user_quiz_data[user_id]["quizzes"].append((title, link))
            title, link = None, None  # Reset for next quiz

    await update.message.reply_text("✅ Quiz saved! Add more quizzes or send /done to finalize.")

async def ask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_quiz_data or not user_quiz_data[user_id]["quizzes"]:
        await update.message.reply_text("⚠ कोई भी क्विज नहीं मिली! पहले क्विज फॉरवर्ड करें।")
        return ConversationHandler.END

    user_quiz_data[user_id]["waiting_for_title"] = True  # Mark waiting state
    await update.message.reply_text("📌 कृपया अपना टाइटल दर्ज करें:")
    return WAITING_FOR_TITLE

async def send_final_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    title = update.message.text.strip()

    if not title:
        await update.message.reply_text("⚠ टाइटल खाली नहीं हो सकता! कृपया एक वैध टाइटल भेजें।")
        return WAITING_FOR_TITLE  # Again wait for title

    if user_id not in user_quiz_data or not user_quiz_data[user_id]["quizzes"]:
        await update.message.reply_text("⚠ कोई भी क्विज नहीं मिली! पहले क्विज फॉरवर्ड करें।")
        return ConversationHandler.END

    user_quiz_data[user_id]["waiting_for_title"] = False  # Reset waiting state

    quizzes = user_quiz_data[user_id]["quizzes"]

    formatted_text = f"🔥 *{title}* 🔥\n📌 *अपनी तैयारी को अगले स्तर पर ले जाएं!*\n\n" \
                     "✦━━━━━━━━━━━━━━✦\n"

    for quiz_title, quiz_link in quizzes:
        formatted_text += (
            f"📖 ── *{quiz_title}* ── 📖\n"
            f"📝 [Start Quiz]({quiz_link})\n"
            "----------------------------------\n"
        )

    formatted_text += "📍 किसी भी विषय पर क्लिक करें और सीधे टेस्ट पर जाएं! 🚀"

    await update.message.reply_text(formatted_text, parse_mode="Markdown", disable_web_page_preview=True)

    # ✅ Clear user data after sending final message
    user_quiz_data.pop(user_id, None)
    return ConversationHandler.END

def main():
    app = Application.builder().token("8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("done", ask_title)],
        states={WAITING_FOR_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_final_quiz)]},
        fallbacks=[],
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_quiz))
    app.add_handler(conv_handler)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
