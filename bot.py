import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

async def extract_quiz_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ✅ Extract quiz title and link using improved regex
    quiz_matches = re.findall(
        r"^(.*?)\s+by\s+@.*?\n.*?External sharing link:\s*(https://t\.me/QuizBot\?start=\S+)", 
        text, re.MULTILINE | re.DOTALL
    )
    
    if not quiz_matches:
        await update.message.reply_text("⚠ कोई वैध क्विज नहीं मिली! कृपया सही फॉरवर्ड किया गया मैसेज भेजें।", parse_mode="Markdown")
        return

    # ✅ **Final Formatted Message**
    formatted_text = "🔥 *महिला सुपरवाइजर परीक्षा 2025* 🔥\n" \
                     "📌 *अपनी तैयारी को अगले स्तर पर ले जाएं!*\n\n" \
                     "✦━━━━━━━━━━━━━━✦\n"

    for title, quiz_link in quiz_matches:
        formatted_text += (
            f"📖 ── *{title.strip()}* ── 📖\n"
            f"📝 [Start Quiz]({quiz_link})\n"
            "----------------------------------\n"
        )

    formatted_text += "📍 किसी भी विषय पर क्लिक करें और सीधे टेस्ट पर जाएं! 🚀"

    await update.message.reply_text(formatted_text, parse_mode="Markdown", disable_web_page_preview=True)

def main():
    app = Application.builder().token("YOUR_BOT_TOKEN").build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, extract_quiz_details))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
