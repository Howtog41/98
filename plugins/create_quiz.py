import random
import string

def generate_quiz_id():
    """Generate a unique quiz ID."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection):
    @bot.message_handler(commands=['create_quiz'])
    def create_quiz(message):
        """Start creating a new quiz."""
        chat_id = message.chat.id
        creating_quizzes[chat_id] = {
            "title": None,
            "questions": [],
            "current_pre_poll_message": None,
            "timer": None,
            "active": True  # To track the active quiz creation process
        }
        bot.send_message(chat_id, "Please send the quiz title.")

    @bot.message_handler(func=lambda message: message.chat.id in creating_quizzes and creating_quizzes[message.chat.id]["active"] and not creating_quizzes[message.chat.id]["title"])
    def set_quiz_title(message):
        """Set the title for the quiz."""
        chat_id = message.chat.id
        creating_quizzes[chat_id]["title"] = message.text
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
        if chat_id in creating_quizzes and creating_quizzes[chat_id]["active"] and creating_quizzes[chat_id]["current_pre_poll_message"]:
            creating_quizzes[chat_id]["current_pre_poll_message"] = None
            bot.send_message(chat_id, "Pre-poll message cleared! 🎉\nNow you can send a new pre-poll message or forward the poll.")
        else:
            bot.send_message(chat_id, "No pre-poll message to undo. You can send a new pre-poll message or forward the poll.")

    @bot.message_handler(func=lambda message: message.chat.id in creating_quizzes and creating_quizzes[message.chat.id]["active"] and creating_quizzes[message.chat.id]["title"] and message.text not in ['/done', '/undo'], content_types=['text', 'photo', 'video'])
    def set_individual_pre_poll_message(message):
        """Set a pre-poll message for the next poll."""
        chat_id = message.chat.id
        if creating_quizzes[chat_id]["timer"] is None:  # Ensure timer is not being set
            if message.content_type == 'text':
                creating_quizzes[chat_id]["current_pre_poll_message"] = {"type": "text", "content": message.text}
            elif message.content_type == 'photo':
                file_id = message.photo[-1].file_id
                creating_quizzes[chat_id]["current_pre_poll_message"] = {"type": "photo", "content": file_id}
            elif message.content_type == 'video':
                file_id = message.video.file_id
                creating_quizzes[chat_id]["current_pre_poll_message"] = {"type": "video", "content": file_id}

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
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id]["active"] or not creating_quizzes[chat_id].get("title"):
            bot.send_message(chat_id, "You are not currently creating a quiz. Use /create_quiz to start.")
            return

        poll = message.poll
        pre_poll_message = creating_quizzes[chat_id]["current_pre_poll_message"]

        # Add the poll with its pre-poll message
        creating_quizzes[chat_id]["questions"].append({
            "pre_poll_message": pre_poll_message,
            "question": poll.question,
            "options": [opt.text for opt in poll.options],
            "correct_option_id": validate_correct_option_id([opt.text for opt in poll.options], poll.correct_option_id),
            "explanation": poll.explanation or "No explanation provided."
        })

        # Reset the current pre-poll message after attaching it to the poll
        creating_quizzes[chat_id]["current_pre_poll_message"] = None

        bot.send_message(
            chat_id,
            f"Poll added: {poll.question}\nSend another pre-poll message (optional) or forward another poll.\n"
            "Type /done when you're finished."
        )
   
    @bot.message_handler(commands=['done'])
    def finish_quiz_creation(message):
        """Complete the quiz creation process and ask for the timer."""
        chat_id = message.chat.id
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id]["active"] or not creating_quizzes[chat_id]["questions"]:
            bot.send_message(chat_id, "No questions added. Use /create_quiz to start again.")
            return
        
        bot.send_message(chat_id, "Enter the open period (in seconds) that will apply to all questions:")
        creating_quizzes[chat_id]["active"] = False  # Deactivate quiz creation, so no more MCQs can be added

    
    @bot.message_handler(func=lambda message: message.chat.id in creating_quizzes and not creating_quizzes[message.chat.id]["active"] and creating_quizzes[message.chat.id]["timer"] is None)
    def set_quiz_timer(message):
        """Set the timer for the quiz."""
        chat_id = message.chat.id
        try:
            open_period = int(message.text)
            if open_period <= 0:
                raise ValueError

            for question in creating_quizzes[chat_id]["questions"]:
                question["open_period"] = open_period  

            quiz_id = generate_quiz_id()
            quiz_data = creating_quizzes.pop(chat_id)
            quiz_data["quiz_id"] = quiz_id  
            quiz_data["participants"] = 0
            quiz_data["leaderboard"] = {}  

            save_quiz_to_db(quiz_id, quiz_data)
            saved_quizzes[quiz_id] = quiz_data
            bot.send_message(chat_id, f"Quiz created successfully! 🎉\nQuiz ID: {quiz_id}\nUse /view_quizzes to see all quizzes.")
        except ValueError:
            bot.send_message(chat_id, "Invalid duration. Please send the duration in seconds (e.g., 120 for 2 minutes).")
