import threading
import time

active_quizzes = {}

def register_handlers(bot, saved_quizzes, creating_quizzes):
    @bot.message_handler(commands=["start"])
    def start_handler(message):
        """Handle the /start command with quiz ID."""
        chat_id = message.chat.id
        # Check if there's a parameter passed with /start
        if len(message.text.split()) > 1:
            param = message.text.split()[1]
            if param.startswith("quiz_"):
                quiz_id = param.split("_", 1)[1]
                start_quiz_handler(bot, chat_id, quiz_id)
            else:
                bot.send_message(chat_id, "Invalid parameter. Please check the link.")
        else:
            bot.send_message(chat_id, "Welcome! Use the commands to interact with me.")

    def start_quiz_handler(bot, chat_id, quiz_id):
        """Start a quiz given its ID."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return

        bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, quiz['timer'])).start()
        send_question(bot, chat_id, quiz_id, 0)

    def quiz_timer(bot, chat_id, quiz_id, duration):
        """Run a timer for the quiz."""
        remaining_time = duration
        while remaining_time > 0:
            if remaining_time % 30 == 0 or remaining_time <= 10:
                bot.send_message(chat_id, f"⏳ Time left: {remaining_time} seconds")
            time.sleep(1)
            remaining_time -= 1
        bot.send_message(chat_id, "⏰ Time's up! The quiz has ended.")

    def send_question(bot, chat_id, quiz_id, question_index):
        """Send a question to the user."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, "Quiz not found.")
            return
        
        questions = quiz["questions"]
        if question_index >= len(questions):
            bot.send_message(chat_id, "Quiz completed!")
            return
        
        question = questions[question_index]
        bot.send_poll(
            chat_id,
            question["question"],
            question["options"],
            type="quiz",
            correct_option_id=question["correct_option_id"],
            is_anonymous=False,
            explanation=question["explanation"]
        )

    @bot.poll_answer_handler()
    def handle_poll_answer(poll_answer):
        """Handle user answers and send the next question."""
        user_id = poll_answer.user.id
        quiz_id = active_quizzes.get(user_id, {}).get("quiz_id")
        if not quiz_id:
            return

        quiz_data = active_quizzes[user_id]
        question_index = quiz_data.get("current_question_index", 0)
        if poll_answer.option_ids[0] == saved_quizzes[quiz_id]["questions"][question_index]["correct_option_id"]:
            quiz_data["score"] += 1

        quiz_data["current_question_index"] += 1
        send_question(bot, quiz_data["chat_id"], quiz_id, quiz_data["current_question_index"])
