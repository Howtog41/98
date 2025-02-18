from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Store quizzes in dictionary {title: link}
quiz_data = {}
admin_id = 1922012735 # Change this to your Telegram user ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /generate_quiz_list to start adding quizzes.")

async def generate_quiz_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != admin_id:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    quiz_data.clear()
    await update.message.reply_text("Send quizzes in the format: `Title - Link`\nType 'Done' when finished.", parse_mode="Markdown")
    context.user_data['adding_quiz'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('adding_quiz', False):
        return
    
    text = update.message.text.strip()
    
    if text.lower() == "done":
        if not quiz_data:
            await update.message.reply_text("No quizzes added! Please add some first.")
            return
        
        formatted_message = generate_formatted_message()
        await update.message.reply_text(formatted_message, parse_mode="Markdown", disable_web_page_preview=True)
        context.user_data['adding_quiz'] = False
        return
    
    try:
        title, link = map(str.strip, text.split("-"))
        if not link.startswith("https://"):
            raise ValueError
        quiz_data[title] = link
        await update.message.reply_text(f"✅ Added: {title}")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid format! Use: `Title - Link`")


def generate_formatted_message():
    header = "🔥 महिला सुपरवाइजर परीक्षा 2025 🔥\n📌 *अपनी तैयारी को अगले स्तर पर ले जाएं!*\n\n✦━━━━━━━━━━━━━━✦\n"
    footer = "✦━━━━━━━━━━━━━━✦\n\n📍 किसी भी विषय पर क्लिक करें और सीधे टेस्ट पर जाएं! 🚀"
    
    body = "\n".join([f"📖 [✦ {title} ✦]({link}) 📖\n---------------------------------------------------------------------------------" for title, link in quiz_data.items()])
    
    return header + body + "\n\n" + footer


def main():
    app = Application.builder().token("8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate_quiz_list", generate_quiz_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
