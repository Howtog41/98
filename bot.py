from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

# ✅ User data store
user_quiz_data = {}
WAITING_FOR_QUIZ = 1
WAITING_FOR_TITLE = 2

async def start_quiz_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /addquiz command ka response - ab agla message ek quiz hoga """
    user_id = update.message.from_user.id
    user_quiz_data[user_id] = {"quizzes": [], "waiting_for_quiz": True, "waiting_for_title": False}
    
    await update.message.reply_text("📌 कृपया क्विज फॉरवर्ड करें।\nकई क्विज भेज सकते हैं, फिर /done करें।")
    return WAITING_FOR_QUIZ

async def collect_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Forwarded quiz message ko store karega """
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_quiz_data or not user_quiz_data[user_id]["waiting_for_quiz"]:
        return

    lines = text.split("\n")
    title, link = None, None

    for line in lines:
        if "by @" in line:
            title = line.split(" by @")[0].strip()
        elif "t.me/QuizBot?start=" in line:
            link = line.strip()

    if title and link:
        user_quiz_data[user_id]["quizzes"].append((title, link))
        await update.message.reply_text("✅ क्विज ऐड हो गया! और क्विज भेजें या /done करें।")
    else:
        await update.message.reply_text("⚠ सही फॉर्मेट में क्विज फॉरवर्ड करें।")

async def ask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /done command ka response - ab title maangega """
    user_id = update.message.from_user.id

    if user_id not in user_quiz_data or not user_quiz_data[user_id]["quizzes"]:
        await update.message.reply_text("⚠ कोई क्विज नहीं मिली! पहले /addquiz भेजें।")
        return

    user_quiz_data[user_id]["waiting_for_quiz"] = False
    user_quiz_data[user_id]["waiting_for_title"] = True

    await update.message.reply_text("📌 कृपया अपना टाइटल दर्ज करें:")
    return WAITING_FOR_TITLE

async def send_final_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ User title bhejta hai, aur final message generate hota hai """
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in user_quiz_data or not user_quiz_data[user_id]["waiting_for_title"]:
        return

    user_quiz_data[user_id]["waiting_for_title"] = False  # Reset waiting state

    quizzes = user_quiz_data[user_id]["quizzes"]

    formatted_text = f"🔥 *{text}* 🔥\n📌 *अपनी तैयारी को अगले स्तर पर ले जाएं!*\n\n" \
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
        entry_points=[CommandHandler("addquiz", start_quiz_collection)],
        states={
            WAITING_FOR_QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_quiz)],
            WAITING_FOR_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_final_quiz)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("done", ask_title))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
