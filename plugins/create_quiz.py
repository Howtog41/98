# plugins/create_quiz.py
creating_quizzes = {}

def register_handlers(bot):
    @bot.message_handler(commands=['create_quiz'])
    def create_quiz(message):
        chat_id = message.chat.id
        creating_quizzes[chat_id] = {
            "title": None,
            "questions": [],
            "timer": None
        }
        bot.send_message(chat_id, "Please send the quiz title.")

    @bot.message_handler(func=lambda message: message.chat.id in creating_quizzes and not creating_quizzes[message.chat.id]["title"])
    def set_quiz_title(message):
        chat_id = message.chat.id
        creating_quizzes[chat_id]["title"] = message.text
        bot.send_message(chat_id, "Quiz title saved! Now forward polls from your channel to add them to the quiz.\nType /done when you're finished.")

    @bot.message_handler(content_types=['poll'])
    def handle_forwarded_poll(message):
        chat_id = message.chat.id
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id].get("title"):
            bot.send_message(chat_id, "You are not currently creating a quiz. Use /create_quiz to start.")
            return
        poll = message.poll
        creating_quizzes[chat_id]["questions"].append({
            "question": poll.question,
            "options": [opt.text for opt in poll.options],
            "correct_option_id": poll.correct_option_id,
            "explanation": poll.explanation or "No explanation provided."
        })
        bot.send_message(chat_id, f"Poll added: {poll.question}\nSend another poll or type /done to finish.")

    @bot.message_handler(commands=['done'])
    def finish_quiz_creation(message):
        chat_id = message.chat.id
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id].get("questions"):
            bot.send_message(chat_id, "No questions added. Use /create_quiz to start again.")
            return
        bot.send_message(chat_id, "Quiz creation complete! Send the quiz duration in seconds.")
