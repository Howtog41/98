import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

active_quizzes = {}
lock = threading.Lock()
saved_quizzes = {}
user_results = {}  # Store user results for leaderboard and admin review

def register_handlers(bot, saved_quizzes, creating_quizzes):
    @bot.message_handler(commands=["start"])
    def start_handler(message):
        """Handle the /start command with quiz ID."""
        chat_id = message.chat.id

        if len(message.text.split()) > 1:
            param = message.text.split()[1]
            if param.startswith("quiz_"):
                quiz_id = param.split("_", 1)[1]
                ask_user_ready(bot, chat_id, quiz_id)
            else:
                bot.send_message(chat_id, "Invalid parameter. Please check the link.")
        else:
            bot.send_message(chat_id, "Welcome! Use the commands to interact with me.")

    def ask_user_ready(bot, chat_id, quiz_id):
        """Send an inline button to confirm readiness."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return

        details = (
            f"📋 **Quiz Details**:\n"
            f"Title: {quiz['title']}\n"
            f"Questions: {len(quiz['questions'])}\n"
            f"Time: {quiz['timer']} seconds\n"
        )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("I'm Ready", callback_data=f"start_quiz_{quiz_id}"))
        bot.send_message(chat_id, details + "Are you ready to start the quiz?", reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_quiz_"))
    def handle_start_quiz(call):
        """Handle the 'I'm Ready' button click."""
        quiz_id = call.data.split("_", 2)[2]
        chat_id = call.message.chat.id
        start_quiz_handler(bot, chat_id, quiz_id)

    def start_quiz_handler(bot, chat_id, quiz_id):
        """Start a quiz given its ID."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return

        with lock:
            if chat_id in active_quizzes:
                bot.send_message(chat_id, "You're already in a quiz! Finish it first before starting a new one.")
                return

            # Initialize active quiz session
            active_quizzes[chat_id] = {
                "quiz_id": quiz_id,
                "chat_id": chat_id,
                "score": 0,
                "current_question_index": 0,
                "start_time": time.time(),
                "end_time": time.time() + quiz["timer"],
            }

        bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, quiz["timer"])).start()
        send_question(bot, chat_id, quiz_id, 0)

    def quiz_timer(bot, chat_id, quiz_id, duration):
        """Run a timer for the quiz and auto-submit on expiry."""
        end_time = time.time() + duration

        while time.time() < end_time:
            remaining_time = int(end_time - time.time())
            if remaining_time % 30 == 0 or remaining_time <= 10:
                hours, minutes = divmod(remaining_time, 3600)
                minutes, seconds = divmod(minutes, 60)
                time_str = f"{hours:02}:{minutes:02}"
                bot.send_message(chat_id, f"⏳ Time left: {remaining_time} seconds")
            time.sleep(1)

            # Check if the quiz was completed manually
            with lock:
                if chat_id not in active_quizzes or active_quizzes[chat_id]["quiz_id"] != quiz_id:
                    return

        # Auto-submit the quiz when time runs out
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
        if "pre_poll_message" in quiz and question_index == 0:
            pre_poll = quiz["pre_poll_message"]
            if pre_poll["type"] == "text":
                bot.send_message(chat_id, pre_poll["content"])
            elif pre_poll["type"] == "photo":
                bot.send_photo(chat_id, pre_poll["content"])
            elif pre_poll["type"] == "video":
                bot.send_video(chat_id, pre_poll["content"])

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
        with lock:
            if chat_id not in active_quizzes:
                bot.send_message(chat_id, "No active quiz found.")
                return

            quiz_data = active_quizzes.pop(chat_id)

        score = quiz_data["score"]
        quiz_id = quiz_data["quiz_id"]
        total_questions = len(saved_quizzes[quiz_id]["questions"])

        # Save the first attempt for the leaderboard
        user_results.setdefault(quiz_id, {})
        if chat_id not in user_results[quiz_id]:
            user_results[quiz_id][chat_id] = score

        # Calculate rank and total participants
        scores = list(user_results[quiz_id].values())
        scores.sort(reverse=True)
        rank = scores.index(score) + 1

        bot.send_message(
            chat_id,
            f"🎉 Quiz completed! Your score: {score}/{total_questions}\n"
            f"📊 Rank: {rank}/{len(scores)} participants.",
        )

    @bot.message_handler(commands=["quiz_stats"])
    def handle_quiz_stats(message):
        """Admin command to view quiz stats by quiz ID."""
        chat_id = message.chat.id
        args = message.text.split()
        if len(args) != 2:
            bot.send_message(chat_id, "Usage: /quiz_stats <quiz_id>")
            return

        quiz_id = args[1]
        if quiz_id not in user_results:
            bot.send_message(chat_id, f"No data found for quiz ID: {quiz_id}")
            return

        stats = user_results[quiz_id]
        result = f"📊 Quiz Stats for ID: {quiz_id}\n"
        result += "\n".join([f"User {user}: {score}" for user, score in stats.items()])
        bot.send_message(chat_id, result)

    
