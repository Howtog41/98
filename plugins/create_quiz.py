import random
import string

def generate_quiz_id():
    """Generate a unique quiz ID."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def register_handlers(bot, saved_quizzes, creating_quizzes):
    @bot.message_handler(commands=['create_quiz'])
    def create_quiz(message):
        """Start creating a new quiz."""
        chat_id = message.chat.id
        creating_quizzes[chat_id] = {
            "title": None,
            "questions": [],
            "timer": None
        }
        bot.send_message(chat_id, "Please send the quiz title.")

    @bot.message_handler(func=lambda message: message.chat.id in creating_quizzes and not creating_quizzes[message.chat.id]["title"])
    def set_quiz_title(message):
        """Set the title for the quiz."""
        chat_id = message.chat.id
        creating_quizzes[chat_id]["title"] = message.text
        bot.send_message(chat_id, "Quiz title saved! 🎉\nNow forward polls from your channel to add them to the quiz.\nType /done when you're finished.")

    @bot.message_handler(content_types=['poll'])
    def handle_forwarded_poll(message):
        """Add a forwarded poll to the quiz."""
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
        """Complete the quiz creation process and ask for the timer."""
        chat_id = message.chat.id
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id]["questions"]:
            bot.send_message(chat_id, "No questions added. Use /create_quiz to start again.")
            return
        bot.send_message(chat_id, "Quiz creation complete! 🎉\nNow, send the quiz duration in seconds (e.g., 120 for 2 minutes).")

    @bot.message_handler(func=lambda message: message.chat.id in creating_quizzes and creating_quizzes[message.chat.id]["title"] and not creating_quizzes[message.chat.id]["timer"])
    def set_quiz_timer(message):
        """Set the timer for the quiz."""
        chat_id = message.chat.id
        try:
            timer = int(message.text)
            if timer <= 0:
                raise ValueError
            creating_quizzes[chat_id]["timer"] = timer
            quiz_id = generate_quiz_id()
            saved_quizzes[quiz_id] = creating_quizzes.pop(chat_id)
            bot.send_message(chat_id, f"Quiz created successfully! 🎉\nQuiz ID: {quiz_id}\nUse /view_quizzes to see all quizzes.")
        except ValueError:
            bot.send_message(chat_id, "Invalid duration. Please send the duration in seconds (e.g., 120 for 2 minutes).")
