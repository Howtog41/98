import threading
import time
from threading import Lock

active_quizzes = {}
active_quizzes_lock = Lock()
saved_quizzes = {}
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

        user_id = chat_id  # Assuming a 1-to-1 chat for simplicity
        with active_quizzes_lock:
            if user_id in active_quizzes:
                bot.send_message(chat_id, "You're already in a quiz! Finish it first before starting a new one.")
                return

            # Initialize active quiz session
            active_quizzes[user_id] = {
                "quiz_id": quiz_id,
                "chat_id": chat_id,
                "score": 0,
                "current_question_index": 0,
                "start_time": time.time()
            }

        bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, quiz['timer'])).start()
        send_question(bot, chat_id, quiz_id, 0)

    def quiz_timer(bot, chat_id, quiz_id, duration):
        """Run a timer for the quiz."""
        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            remaining_time = int(end_time - time.time())

            if remaining_time in {30, 15, 10, 5} or remaining_time <= 3:
                bot.send_message(chat_id, f"⏳ Time left: {remaining_time} seconds")
            time.sleep(1)

        # Check if quiz already completed
        user_id = chat_id
        with active_quizzes_lock:
            if user_id not in active_quizzes or active_quizzes[user_id].get("quiz_id") != quiz_id:
                return

        bot.send_message(chat_id, "⏰ Time's up! The quiz has ended.")
        finalize_quiz(bot, chat_id)

    def send_question(bot, chat_id, quiz_id, question_index):
        """Send a question to the user."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, "Quiz not found.")
            return

        questions = quiz["questions"]
        if question_index >= len(questions):
            finalize_quiz(bot, chat_id)
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

    def finalize_quiz(bot, chat_id):
        """Finalize the quiz and show the user's score."""
        user_id = chat_id
        with active_quizzes_lock:
            if user_id not in active_quizzes:
                bot.send_message(chat_id, "No active quiz found.")
                return

            quiz_data = active_quizzes.pop(user_id)

        score = quiz_data["score"]
        quiz_id = quiz_data["quiz_id"]
        total_questions = len(saved_quizzes[quiz_id]["questions"])

        bot.send_message(chat_id, f"🎉 Quiz completed! Your score: {score}/{total_questions}")

    @bot.poll_answer_handler()
    def handle_poll_answer(poll_answer):
        """Handle user answers and send the next question."""
        user_id = poll_answer.user.id
        with active_quizzes_lock:
            if user_id not in active_quizzes:
                return

            quiz_data = active_quizzes[user_id]
            quiz_id = quiz_data["quiz_id"]
            question_index = quiz_data.get("current_question_index", 0)

            # Check answer correctness
            correct_option_id = saved_quizzes[quiz_id]["questions"][question_index]["correct_option_id"]
            if poll_answer.option_ids[0] == correct_option_id:
                quiz_data["score"] += 1

            # Move to next question
            quiz_data["current_question_index"] += 1

        send_question(bot, quiz_data["chat_id"], quiz_id, quiz_data["current_question_index"])
