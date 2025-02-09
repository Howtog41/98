import random
import string


def generate_quiz_id():
    """Generate a unique quiz ID."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def register_handlers(bot, save_quiz_to_db, fetch_quiz_from_db):
    @bot.message_handler(commands=['create_quiz'])
    def create_quiz(message):
        """Start creating a new quiz."""
        chat_id = message.chat.id
        # Create a new quiz template
        new_quiz = {
            "_id": chat_id,
            "title": None,
            "questions": [],
            "current_pre_poll_message": None,
            "timer": None,
            "active": True  # To track the active quiz creation process
        }
        save_quiz_to_db(new_quiz)
        bot.send_message(chat_id, "Please send the quiz title.")

    @bot.message_handler(func=lambda message: fetch_quiz_from_db(message.chat.id) and fetch_quiz_from_db(message.chat.id)["active"] and not fetch_quiz_from_db(message.chat.id)["title"])
    def set_quiz_title(message):
        """Set the title for the quiz."""
        chat_id = message.chat.id
        quiz = fetch_quiz_from_db(chat_id)
        quiz["title"] = message.text
        save_quiz_to_db(quiz)
        bot.send_message(
            chat_id,
            "Quiz title saved! 🎉\nNow send a pre-poll message (optional) for the next poll (text, image, or video).\n"
            "If you don't want to add a pre-poll message, simply forward the poll.\n"
            "Type /done when you're finished.\n"
            "If you sent a pre-poll message by mistake, use /undo to reset it."
        )

    @bot.message_handler(commands=['undo'])
    def undo_pre_poll_message(message):
        """Undo the last pre-poll message."""
        chat_id = message.chat.id
        quiz = fetch_quiz_from_db(chat_id)
        if quiz and quiz["active"] and quiz["current_pre_poll_message"]:
            quiz["current_pre_poll_message"] = None
            save_quiz_to_db(quiz)
            bot.send_message(chat_id, "Pre-poll message cleared! 🎉\nNow you can send a new pre-poll message or forward the poll.")
        else:
            bot.send_message(chat_id, "No pre-poll message to undo. You can send a new pre-poll message or forward the poll.")

    @bot.message_handler(func=lambda message: fetch_quiz_from_db(message.chat.id) and fetch_quiz_from_db(message.chat.id)["active"] and fetch_quiz_from_db(message.chat.id)["title"] and message.text not in ['/done', '/undo'], content_types=['text', 'photo', 'video'])
    def set_individual_pre_poll_message(message):
        """Set a pre-poll message for the next poll."""
        chat_id = message.chat.id
        quiz = fetch_quiz_from_db(chat_id)
        if message.content_type == 'text':
            quiz["current_pre_poll_message"] = {"type": "text", "content": message.text}
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            quiz["current_pre_poll_message"] = {"type": "photo", "content": file_id}
        elif message.content_type == 'video':
            file_id = message.video.file_id
            quiz["current_pre_poll_message"] = {"type": "video", "content": file_id}

        save_quiz_to_db(quiz)
        bot.send_message(
            chat_id,
            "Pre-poll message saved! 🎉\nNow forward the poll this message applies to.\n"
            "If you sent this message by mistake, use /undo to reset it."
        )

    def validate_correct_option_id(options, correct_option_id):
        if 0 <= correct_option_id < len(options):
            return correct_option_id
        else:
            raise ValueError(f"Invalid correct_option_id: {correct_option_id}. Options: {options}")

    @bot.message_handler(content_types=['poll'])
    def handle_forwarded_poll(message):
        """Add a forwarded poll to the quiz, along with its pre-poll message."""
        chat_id = message.chat.id
        quiz = fetch_quiz_from_db(chat_id)
        if not quiz or not quiz["active"] or not quiz.get("title"):
            bot.send_message(chat_id, "You are not currently creating a quiz. Use /create_quiz to start.")
            return

        poll = message.poll
        pre_poll_message = quiz["current_pre_poll_message"]

        # Add the poll with its pre-poll message
        quiz["questions"].append({
            "pre_poll_message": pre_poll_message,
            "question": poll.question,
            "options": [opt.text for opt in poll.options],
            "correct_option_id": validate_correct_option_id([opt.text for opt in poll.options], poll.correct_option_id),
            "explanation": poll.explanation or "No explanation provided."
        })

        # Reset the current pre-poll message after attaching it to the poll
        quiz["current_pre_poll_message"] = None
        save_quiz_to_db(quiz)

        bot.send_message(
            chat_id,
            f"Poll added: {poll.question}\nSend another pre-poll message (optional) or forward another poll.\n"
            "Type /done when you're finished."
        )

    @bot.message_handler(commands=['done'])
    def finish_quiz_creation(message):
        """Complete the quiz creation process and ask for the timer."""
        chat_id = message.chat.id
        quiz = fetch_quiz_from_db(chat_id)
        if not quiz or not quiz["active"] or not quiz["questions"]:
            bot.send_message(chat_id, "No questions added. Use /create_quiz to start again.")
            return

        # Mark the quiz creation process as inactive
        quiz["active"] = False
        save_quiz_to_db(quiz)

        bot.send_message(chat_id, "Quiz creation complete! 🎉\nNow, send the quiz duration in seconds (e.g., 120 for 2 minutes).")

    @bot.message_handler(func=lambda message: fetch_quiz_from_db(message.chat.id) and not fetch_quiz_from_db(message.chat.id)["active"] and fetch_quiz_from_db(message.chat.id)["timer"] is None)
    def set_quiz_timer(message):
        """Set the timer for the quiz."""
        chat_id = message.chat.id
        quiz = fetch_quiz_from_db(chat_id)
        try:
            timer = int(message.text)
            if timer <= 0:
                raise ValueError
            quiz["timer"] = timer
            save_quiz_to_db(quiz)
            bot.send_message(chat_id, f"Quiz created successfully! 🎉\nQuiz ID: {quiz['_id']}\nUse /view_quizzes to see all quizzes.")
        except ValueError:
            bot.send_message(chat_id, "Invalid duration. Please send the duration in seconds (e.g., 120 for 2 minutes).")
