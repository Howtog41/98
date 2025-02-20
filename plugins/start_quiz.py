import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

active_quizzes = {}
lock = threading.Lock()  # Thread-safe lock for active_quizzes
saved_quizzes = {}
leaderboards = {}  # Store leaderboards for each quiz

def register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection):
    global db_collection  # Define it globally within this module
    db_collection = quizzes_collection  # Assign MongoDB collection to a local variable
    @bot.message_handler(commands=["start"])
    def start_handler(message):
        """Handle the /start command with quiz ID."""
        chat_id = message.chat.id
        chat_type = message.chat.type  # Check if it's private or a group

        if len(message.text.split()) > 1:
            param = message.text.split()[1]
            if param.startswith("quiz_"):
                quiz_id = param.split("_", 1)[1]
                if chat_type == "private":
                    # If it's a personal chat, ask user if they are ready
                    ask_user_ready(bot, chat_id, quiz_id)
                else:
                    # If it's a group chat, start group quiz handler
                    start_group_quiz(bot, chat_id, quiz_id)
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
        message_id = call.message.message_id  # Get message ID

        # Remove the inline button by editing the message
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)

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
                "end_time": time.time() + quiz["timer"]
            }

        bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, quiz["timer"])).start()
        send_question(bot, chat_id, quiz_id, 0)

    def quiz_timer(bot, chat_id, quiz_id, duration):
        """Run a timer for the quiz and auto-submit on expiry."""
        end_time = time.time() + duration

        while time.time() < end_time:
            remaining_time = int(end_time - time.time())
            if remaining_time in [10500, 7200, 3600, 1800, 900, 600, 300, 60, 30, 20, 10, 5, 3, 1]:
                hours, remainder = divmod(remaining_time, 3600)
                minutes, seconds = divmod(remainder, 60)
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

            # Load quiz from MongoDB
            quiz = db_collection.find_one({"quiz_id": quiz_id})
            if not quiz:
                bot.send_message(chat_id, "Error: Quiz not found in database.")
                return

            # Send a loading message before processing
            loading_msg = bot.send_message(chat_id, "⏳ Processing your results...")

            # Fetch existing leaderboard or initialize if missing
            leaderboard = quiz.get("leaderboard", [])

             # ✅ Fix: Convert to list if stored as a dictionary
            if isinstance(leaderboard, dict):
                leaderboard = list(leaderboard.values())
            # Print for debugging
            
            # Check if user already exists in leaderboard
            user_exists = any(entry["chat_id"] == chat_id for entry in leaderboard)
            if not user_exists:
                leaderboard.append({"chat_id": chat_id, "score": score})

            # Sort leaderboard by score
            leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)

            # Save updated leaderboard to MongoDB
            update_result = db_collection.update_one(
                {"quiz_id": quiz_id},
                {"$set": {"leaderboard": leaderboard, "participants": len(leaderboard)}}
            )

           
            # Get user rank
            rank = next((i + 1 for i, entry in enumerate(leaderboard) if entry["chat_id"] == chat_id), None)
            if rank is None:
                rank = len(leaderboard)

            # Fetch quiz details
            quiz_title = quiz.get("title", "Unknown Quiz")
            total_questions = quiz.get("total_questions", len(quiz.get("questions", [])))
            total_participants = len(leaderboard)

            # Ensure leaderboard has data
            if not leaderboard:
                bot.edit_message_text("No participants found for this quiz.", chat_id, message_id=loading_msg.message_id)
                return

            # Get top 5 users
            top_5 = leaderboard[:5]

            # Create leaderboard message
            leaderboard_text = f"📊 Quiz Title: {quiz_title}\n"
            leaderboard_text += f"🎉 Quiz completed! Your score: {score}/{total_questions}\n"
            leaderboard_text += f"🏅 Your Rank: {rank}/{total_participants}\n\n"

            # Show top 5 users
            leaderboard_text += "🏆 Top 5 Users:\n"
            for i, entry in enumerate(top_5, start=1):
                user_display_name = get_user_display_name(bot, entry["chat_id"])
                leaderboard_text += f"{i}. {user_display_name} - {entry['score']} points\n"

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
        quiz = db_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            bot.send_message(message.chat.id, f"No leaderboard found for Quiz ID: {quiz_id}")
            return
        title = quiz["title"]
        leaderboard = quiz.get("leaderboard", [])
        sorted_leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)
        # Limit entries (set max_entries = 20)
        max_entries = 20
        leaderboard = leaderboard[:max_entries]
        leaderboard_text = f"📊 Leaderboard for '{title}':\n\n"
        message_parts = []  # ✅ Initialize message_parts before use

        for rank, entry in enumerate(sorted_leaderboard, start=1):
            user_display_name = get_user_display_name(bot, entry["chat_id"])
            line = f"{rank}. {user_display_name} - {entry['score']} points\n"
        
            # Check if message length exceeds Telegram's limit
            if len(leaderboard_text) + len(line) > 4000:
                message_parts.append(leaderboard_text)  # Save current part
                leaderboard_text = ""  # Start a new message

            leaderboard_text += line

        message_parts.append(leaderboard_text)  # Add last part

        # Send messages
        for part in message_parts:
            bot.send_message(message.chat.id, part)


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


    def start_group_quiz(bot, chat_id, quiz_id):
        """Start the quiz in a group with a 40-second timer for each question."""
        if quiz_id not in saved_quizzes:
            bot.send_message(chat_id, "Quiz not found. Please check the quiz ID.")
            return
    
        bot.send_message(chat_id, f"🎉 Group Quiz Started! 🎉\nQuiz ID: {quiz_id}\nEach question has **40 seconds** to answer.")
    
        active_quizzes[chat_id] = {
            "quiz_id": quiz_id,
            "questions": saved_quizzes[quiz_id],  # Load questions
            "current_index": 0,
            "responses": {},  # Track user responses
            "participants": set(),  # Unique participants
        }

        question_index = 0  

        # Start first question
        send_next_question(bot, chat_id, quiz_id, question_index)

    def send_next_question(bot, chat_id, quiz_id, question_index):
        """Send the next question with a 40-second timer."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, "Quiz not found.")
            return

        questions = quiz["questions"]
        total_questions = len(questions) 
        if question_index >= len(questions):
            show_leaderboard(bot, chat_id)
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
            is_anonymous=False, # Ensure this is not passed twice
            open_period=40
        )

        # Update active quiz index
        active_quizzes[chat_id]["current_index"] = question_index

       

    @bot.poll_handler()
    def handle_poll_results(poll):
        """Handle poll results and send the next question automatically."""
        chat_id = active_poll_chats.get(poll.id)
        if not chat_id or chat_id not in active_quizzes:
            return

        quiz_data = active_quizzes[chat_id]
        current_index = quiz_data["current_index"]

        # If more questions are left, send the next one
        if current_index + 1 < len(quiz_data["questions"]):
            send_next_question(bot, chat_id, quiz_data["quiz_id"], current_index + 1)
        else:
            show_leaderboard(bot, chat_id)

   

    @bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
    def handle_answer(bot, call):
        """Handle user answers in group quiz."""
        data = call.data.split("_")
        chat_id = int(data[1])
        question_index = int(data[2])
        selected_option = int(data[3])
        user_id = call.from_user.id

        if chat_id not in active_quizzes:
            return

        quiz_data = active_quizzes[chat_id]
        correct_answer = quiz_data["questions"][question_index]["correct_answer"]

        # Track user's first response only
        if user_id not in quiz_data["responses"]:
            quiz_data["responses"][user_id] = 0  # Initialize user score

        if user_id not in quiz_data["participants"]:
            quiz_data["participants"].add(user_id)  # Add user to participants

        if selected_option == correct_answer:
            quiz_data["responses"][user_id] += 1  # Increase score for correct answer

        bot.answer_callback_query(call.id, "Answer recorded!")  # Confirm answer selection

    def show_leaderboard(bot, chat_id):
        """Display leaderboard at the end of the quiz."""
        if chat_id not in active_quizzes:
            return

        quiz_data = active_quizzes[chat_id]
        scores = quiz_data["responses"]

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
        leaderboard_text = "🏆 **Final Leaderboard** 🏆\n"
        for i, (user_id, score) in enumerate(sorted_scores, start=1):
            leaderboard_text += f"{i}. [User {user_id}](tg://user?id={user_id}) - {score} points\n"

        bot.send_message(chat_id, leaderboard_text, parse_mode="Markdown")
        del active_quizzes[chat_id]  # Cleanup after quiz ends
