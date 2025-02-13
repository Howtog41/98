import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

active_quizzes = {}
lock = threading.Lock()  # Thread-safe lock for active_quizzes
saved_quizzes = {}
leaderboards = {}  # Store leaderboards for each quiz

def register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db):
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

        
        title = quiz["title"]
        timer = quiz["timer"]
        minutes, seconds = divmod(timer, 60)
        time_str = f"{minutes} min {seconds} sec"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("I'm Ready", callback_data=f"start_quiz_{quiz_id}"))
        bot.send_message(
            chat_id,
            f"📝 **Quiz Title:** {title}\n⏳ **Duration:** {time_str}\n\n🎉 **Are you ready to begin?**\n\n📢 *Aapko har minute par bataya jayega ki kitna time bacha hai!*",
            reply_markup=markup,
            parse_mode="Markdown"
        )

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
                "last_activity": time.time(),  # Track last activity time
                "paused": False
            }

        bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, quiz["timer"]), daemon=True).start()
        send_question(bot, chat_id, quiz_id, 0)

    def quiz_timer(bot, chat_id, quiz_id, duration):
        """Run a timer for the quiz and auto-submit on expiry."""
        end_time = time.time() + duration

        while True:
            with lock:
                if chat_id not in active_quizzes or active_quizzes[chat_id]["quiz_id"] != quiz_id:
                    return  

                if active_quizzes[chat_id].get("paused"):
                    active_quizzes[chat_id]["remaining_time"] = int(end_time - time.time())
                    return  # Timer stops when quiz is paused
            
            remaining_time = int(end_time - time.time())
            if remaining_time <= 0:
                break  # Time expired
                
            if remaining_time % 20 == 0 or remaining_time <= 10:
                hours, minutes = divmod(remaining_time, 3600)
                minutes, seconds = divmod(minutes, 60)
                time_parts = []
                if hours > 0:
                    time_parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
                if minutes > 0:
                    time_parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
                if seconds > 0:
                    time_parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
                time_str = ", ".join(time_parts)
                bot.send_message(chat_id, f"⏳ Time left: {time_str}")

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
        with lock:
            if chat_id in active_quizzes:
                active_quizzes[chat_id]["last_activity"] = time.time()
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, "Quiz not found.")
            return

        questions = quiz["questions"]
        total_questions = len(questions) 
        if question_index >= len(questions):
            finalize_quiz(bot, chat_id)
            return

        question = questions[question_index]
        pre_poll_message = question.get("pre_poll_message")
        if pre_poll_message:
            if pre_poll_message["type"] == "text":
                bot.send_message(chat_id, pre_poll_message["content"])
            elif pre_poll_message["type"] == "photo":
                bot.send_photo(chat_id, pre_poll_message["content"])
            elif pre_poll_message["type"] == "video":
                bot.send_video(chat_id, pre_poll_message["content"])

        # Add numbering to the question
        numbered_question = f"Q{question_index + 1}/{total_questions}: {question['question']}"
    
        
        bot.send_poll(
            chat_id=chat_id,
            question=numbered_question,
            options=question["options"],
            type="quiz",
            correct_option_id=question["correct_option_id"],
            explanation=question["explanation"],
            is_anonymous=False  # Ensure this is not passed twice
        )
        threading.Thread(target=check_inactivity, args=(bot, chat_id, quiz_id), daemon=True).start()
    def get_user_display_name(bot, chat_id):
        """Fetch user's display name (username or first + last name)."""
        try:
            user_info = bot.get_chat(chat_id)
            if user_info.username:
                return f"@{user_info.username}"
            elif user_info.first_name:
                return f"{user_info.first_name} {user_info.last_name}".strip() if user_info.last_name else user_info.first_name
            else:
                return f"User {chat_id}"  # Fallback if no name is available
        except Exception:
            return f"User {chat_id}"  # Fallback in case of an error

    
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
            quiz_title = saved_quizzes[quiz_id]["title"]
 
            # Send a loading message before processing
            loading_msg = bot.send_message(chat_id, "⏳ Processing your results...")

            # Add user to leaderboard
            if quiz_id not in leaderboards:
                leaderboards[quiz_id] = []

            user_exists = any(entry["chat_id"] == chat_id for entry in leaderboards[quiz_id])
            if not user_exists:
                leaderboards[quiz_id].append({"chat_id": chat_id, "score": score})

       
            # Calculate rank
            sorted_leaderboard = sorted(leaderboards[quiz_id], key=lambda x: x["score"], reverse=True)
            rank = next((i + 1 for i, entry in enumerate(sorted_leaderboard) if entry["chat_id"] == chat_id), len(sorted_leaderboard))
            total_participants = len(sorted_leaderboard) 
        
        # Create leaderboard message
        leaderboard_text = f"📊 Quiz Title: {quiz_title}\n"
        leaderboard_text += f"🎉 Quiz completed! Your score: {score}/{total_questions}\n"
        leaderboard_text += f"🏅 Your Rank: {rank}/{total_participants}\n\n"
    
        # Show top 5 users
        leaderboard_text += "🏆 Top 5 Users:\n"
        for rank, entry in enumerate(sorted_leaderboard[:5], start=1):
            user_display_name = get_user_display_name(bot, entry["chat_id"])
            leaderboard_text += f"{rank}. {user_display_name} - {entry['score']} points\n"

        # Show the user's own position after top 5
        user_display_name = get_user_display_name(bot, chat_id)
        leaderboard_text += f"\nYou are ranked #{rank} - {user_display_name} with {score} points."

        # Send leaderboard message
        bot.edit_message_text(leaderboard_text, chat_id, message_id=loading_msg.message_id)

    def is_admin(chat_id):
        admin_ids = [1922012735]  # Replace with actual admin IDs
        return chat_id in admin_ids

    @bot.message_handler(commands=["leaderboard"])
    def leaderboard_handler(message):
        """Allow admin to view the leaderboard."""
        if not is_admin(message.chat.id):  # Replace with your admin check logic
            bot.send_message(message.chat.id, "You are not authorized to view the leaderboard.")
            return

        args = message.text.split()
        if len(args) < 2:
            bot.send_message(message.chat.id, "Please provide the quiz ID. Example: /leaderboard quiz_123")
            return

        quiz_id = args[1]
        if quiz_id not in leaderboards:
            bot.send_message(message.chat.id, f"No leaderboard found for Quiz ID: {quiz_id}")
            return

        quiz_title = saved_quizzes[quiz_id]["title"]
        sorted_leaderboard = sorted(leaderboards[quiz_id], key=lambda x: x["score"], reverse=True)
        leaderboard_text = f"📊 Leaderboard for '{quiz_title}':\n\n"
        for rank, entry in enumerate(sorted_leaderboard, start=1):
            user_display_name = get_user_display_name(bot, entry["chat_id"])
            leaderboard_text += f"{rank}. {user_display_name} - {entry['score']} points\n"

        bot.send_message(message.chat.id, leaderboard_text)


    @bot.poll_answer_handler()
    def handle_poll_answer(poll_answer):
        """Handle user answers and send the next question."""
        user_id = poll_answer.user.id
        with lock:
            if user_id not in active_quizzes:
                return

            quiz_data = active_quizzes[user_id]
            quiz_id = quiz_data["quiz_id"]
            question_index = quiz_data.get("current_question_index", 0)


            # ✅ Jab bhi user answer tick kare, quiz active ho jaye
            active_quizzes[user_id]["paused"] = False
            active_quizzes[user_id]["last_activity"] = time.time()

            # ✅ Agar quiz paused thi, to timer resume kare
            remaining_time = active_quizzes[user_id].get("remaining_time", 0)
            if remaining_time > 0:
                threading.Thread(target=quiz_timer, args=(bot, user_id, quiz_id, remaining_time), daemon=True).start()
                active_quizzes[user_id].pop("remaining_time", None)  # Timer reset kare

            
            # Check answer correctness
            correct_option_id = saved_quizzes[quiz_id]["questions"][question_index]["correct_option_id"]
            if poll_answer.option_ids[0] == correct_option_id:
                quiz_data["score"] += 1

            # Move to next question
            quiz_data["current_question_index"] += 1

            
            
        next_question_index = quiz_data["current_question_index"]

    # Send the next question or finalize the quiz if completed
        if next_question_index < len(saved_quizzes[quiz_id]["questions"]):
            send_question(bot, quiz_data["chat_id"], quiz_id, next_question_index)
        else:
            finalize_quiz(bot, quiz_data["chat_id"])

    def check_inactivity(bot, chat_id, quiz_id):
        """Check if the user is inactive and pause the quiz."""
        while True:
            time.sleep(30)  # 5 minutes wait
            with lock:
                if chat_id in active_quizzes:
                    last_activity = active_quizzes[chat_id]["last_activity"]
                    if time.time() - last_activity >= 30:  # 5 minutes of inactivity
                        active_quizzes[chat_id]["paused"] = True
                        bot.send_message(
                            chat_id,
                            "⏸️ **Quiz Paused due to inactivity.**\n\n⚡ *Select any option to continue the test.*",
                            parse_mode="Markdown"
                        )
                        return


    @bot.callback_query_handler(func=lambda call: call.data.startswith("mcq_"))
    def handle_mcq_selection(call):
        """Handle MCQ selection and auto-resume if paused."""
        chat_id = call.message.chat.id
        quiz_id, selected_option = call.data.split("_", 2)[1:]

        with lock:
            if chat_id in active_quizzes:
                if active_quizzes[chat_id].get("paused"):
                    # Auto-resume the quiz when user selects an MCQ
                    active_quizzes[chat_id]["paused"] = False
                    active_quizzes[chat_id]["last_activity"] = time.time()
                
                    remaining_time = active_quizzes[chat_id].get("remaining_time", 0)
                    if remaining_time > 0:
                        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, remaining_time), daemon=True).start()
                        active_quizzes[chat_id].pop("remaining_time", None)

                # Process user's answer and move to the next question
                process_answer(bot, chat_id, quiz_id, selected_option)
