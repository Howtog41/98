from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ✅ Temporary storage to collect multiple quizzes
user_quiz_data = {}

async def collect_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_quiz_data:
        user_quiz_data[user_id] = []

    lines = text.split("\n")
    title = None
    link = None

    for line in lines:
        if "by @" in line:
            title = line.split(" @")[0].strip()  # Extract title
        elif "t.me/QuizBot?start=" in line:
            link = line.strip()  # Extract link

        if title and link:
            user_quiz_data[user_id].append((title, link))
            title, link = None, None  # Reset for next quiz

    await update.message.reply_text("✅ Quiz saved! Add more quizzes or send /done to finalize.")

async def send_final_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_quiz_data or not user_quiz_data[user_id]:
        await update.message.reply_text("⚠ कोई भी क्विज नहीं मिली! पहले क्विज फॉरवर्ड करें।", parse_mode="Markdown")
        return

    # ✅ **Final Formatted Message**
    formatted_text = "🔥 *महिला सुपरवाइजर परीक्षा 2025* 🔥\n" \
                     "📌 *अपनी तैयारी को अगले स्तर पर ले जाएं!*\n\n" \
                     "✦━━━━━━━━━━━━━━✦\n"

    for title, quiz_link in user_quiz_data[user_id]:
        formatted_text += (
            f"📖 ── *{title}* ── 📖\n"
            "----------------------------------\n"
            f".      📝 [Start Quiz]({quiz_link})\n"
            "----------------------------------\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        )

    formatted_text += "📍 किसी भी विषय पर क्लिक करें और सीधे टेस्ट पर जाएं! 🚀"

    # ✅ Send the final message
    await update.message.reply_text(formatted_text, parse_mode="Markdown", disable_web_page_preview=True)

    # ✅ Clear user data after sending the message
    user_quiz_data[user_id] = []

def main():
    app = Application.builder().token("8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI").build()
    
    # ✅ Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_quiz))
    app.add_handler(CommandHandler("done", send_final_quiz))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
