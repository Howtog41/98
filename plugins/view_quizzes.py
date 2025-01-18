# plugins/view_quizzes.py
saved_quizzes = {}

def register_handlers(bot):
    @bot.message_handler(commands=['view_quizzes'])
    def view_quizzes(message):
        chat_id = message.chat.id
        if not saved_quizzes:
            bot.send_message(chat_id, "No quizzes available.")
            return
        response = "Your Quizzes:\n\n"
        for quiz_id, quiz in saved_quizzes.items():
            response += f"{quiz['title']} 📝 {len(quiz['questions'])} Questions\nStart: /start_{quiz_id}\n\n"
        bot.send_message(chat_id, response)
