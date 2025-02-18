import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

async def extract_quiz_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Extract all quiz titles and links
    quiz_matches = re.findall(r"^(.*?)\s+by\s+@.*?\n.*?(https://t\.me/QuizBot\?start=\S+)", text, re.MULTILINE)
    
    if not quiz_matches:
        await update.message.reply_text("⚠ कोई वैध क्विज नहीं मिली!", parse_mode="Markdown")
        return

    # ✅ **Final Formatted Message**
    formatted_text = "🔥 महिला सुपरवाइजर परीक्षा 2025 🔥\n" \
                     "📌 *अपनी तैयारी को अगले स्तर पर ले जाएं!*\n\n" \
                     "✦━━━━━━━━━━━━━━✦\n"

    for title, quiz_link in quiz_matches:
        formatted_text += (
            f"┌───────────────────────────┐\n"
            f"│ 📖 *{title}* 📖 │\n"
            f"│ [Start Quiz]({quiz_link}) │\n"
            f"└───────────────────────────┘\n"
            "----------------------------------\n"
        )

    formatted_text += "📍 किसी भी विषय पर क्लिक करें और सीधे टेस्ट पर जाएं! 🚀"

    await update.message.reply_text(formatted_text, parse_mode="Markdown", disable_web_page_preview=True)

def main():
    app = Application.builder().token("8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI").build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, extract_quiz_details))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
