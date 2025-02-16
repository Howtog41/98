import threading
import time
import asyncio
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

active_quizzes = {}
lock = threading.Lock()  # Thread-safe lock for active_quizzes
saved_quizzes = {}
leaderboards = {}  # Store leaderboards for each quiz

def register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection):
    global db_collection
    db_collection = quizzes_collection  

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

    # ✅ Corrected: Async Callback Handler for Inline Button
    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_quiz_"))
    async def handle_start_quiz(call):
        """Handle the 'I'm Ready' button click."""
        quiz_id = call.data.split("_", 2)[2]
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        # Remove the inline button
        await bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)

        # ✅ Ensure we await the quiz start function
        await start_quiz_handler(bot, chat_id, quiz_id)



    
    async def start_quiz_handler(bot, chat_id, quiz_id):
        """Start a quiz given its ID."""
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            await bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return

        with lock:
            if chat_id in active_quizzes:
                await bot.send_message(
                    chat_id, 
                    "📢 *आप पहले से ही एक क्विज़ में भाग ले रहे हैं\\!* ⏳\n"
                    "कृपया पहले इसे पूर्ण करें, तभी आप नई क्विज़ प्रारंभ कर सकेंगे\\! ✅\n"
                    "जब तक वर्तमान क्विज़ संपन्न नहीं होती, नई क्विज़ आरंभ नहीं होगी\\! 🚫",
                    parse_mode="MarkdownV2"
                )
                return

            # Initialize active quiz session
            active_quizzes[chat_id] = {
                "quiz_id": quiz_id,
                "chat_id": chat_id,
                "score": 0,
                "current_question_index": 0,
                "start_time": asyncio.get_event_loop().time(),  # ✅ Use asyncio time
                "end_time": asyncio.get_event_loop().time() + quiz["timer"],
                "last_activity": asyncio.get_event_loop().time(),
                "paused": False
            }

        await bot.send_message(chat_id, "The quiz is starting now! Good luck!")

        # ✅ Correct way to start quiz timer asynchronously
        asyncio.create_task(quiz_timer(bot, chat_id, quiz_id, quiz["timer"]))

        # ✅ Send first question asynchronously
        await send_question(bot, chat_id, quiz_id, 0)



    async def quiz_timer(bot, chat_id, quiz_id, duration):
        """Run a timer for the quiz and auto-submit on expiry."""
        end_time = asyncio.get_event_loop().time() + duration  # Use asyncio time

        while True:
            await asyncio.sleep(1)  # ✅ Non-blocking sleep

            with lock:
                # ✅ Agar quiz delete ho gaya, to timer band ho jaye
                if chat_id not in active_quizzes or active_quizzes[chat_id]["quiz_id"] != quiz_id:
                    return  

                # ✅ Agar quiz paused hai, to wait kare, lekin loop continue rakhe
                if active_quizzes[chat_id].get("paused"):
                    active_quizzes[chat_id]["remaining_time"] = int(end_time - asyncio.get_event_loop().time())
                    await asyncio.sleep(1)  # ✅ Wait and retry instead of returning
                    continue  # Loop ko chalne do

            # ✅ Remaining time calculate kare
            remaining_time = int(end_time - asyncio.get_event_loop().time())
            if remaining_time <= 0:
                break  # ⏰ Time expired

            # ✅ Specific time pe warning bheje
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

                time_str = " and ".join(time_parts)
                await bot.send_message(chat_id, f"⏳ Time left: {time_str}")

        # ⏰ Auto-submit the quiz when time runs out
        await bot.send_message(chat_id, "⏰ Time's up! The quiz has ended.")
        await finalize_quiz(bot, chat_id)

    async def send_question(bot, chat_id, quiz_id, question_index):
        """Send a question to the user."""
        with lock:
            if chat_id in active_quizzes:
                active_quizzes[chat_id]["last_activity"] = asyncio.get_event_loop().time()

        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            await bot.send_message(chat_id, "Quiz not found.")
            return

        questions = quiz["questions"]
        total_questions = len(questions)
        if question_index >= len(questions):
            await finalize_quiz(bot, chat_id)
            return

        question = questions[question_index]
        pre_poll_message = question.get("pre_poll_message")
    
        if pre_poll_message:
            if pre_poll_message["type"] == "text":
                await bot.send_message(chat_id, pre_poll_message["content"])
            elif pre_poll_message["type"] == "photo":
                await bot.send_photo(chat_id, pre_poll_message["content"])
            elif pre_poll_message["type"] == "video":
                await bot.send_video(chat_id, pre_poll_message["content"])

        # Add numbering to the question
        numbered_question = f"Q{question_index + 1}/{total_questions}: {question['question']}"

        await bot.send_poll(
            chat_id=chat_id,
            question=numbered_question,
            options=question["options"],
            type="quiz",
            correct_option_id=question["correct_option_id"],
            explanation=question["explanation"],
            is_anonymous=False
        )

        # ✅ Instead of threading.Thread, use asyncio.create_task
        asyncio.create_task(check_inactivity(bot, chat_id, quiz_id))
    
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
    async def handle_poll_answer(poll_answer):
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
            active_quizzes[user_id]["last_activity"] = asyncio.get_event_loop().time()

            # ✅ Agar quiz paused thi, to timer resume kare
            remaining_time = active_quizzes[user_id].get("remaining_time", 0)
            if remaining_time > 0:
                asyncio.create_task(quiz_timer(bot, user_id, quiz_id, remaining_time))
                active_quizzes[user_id].pop("remaining_time", None)  # Timer reset kare

            # ✅ Check answer correctness
            correct_option_id = saved_quizzes[quiz_id]["questions"][question_index]["correct_option_id"]
            if poll_answer.option_ids[0] == correct_option_id:
                quiz_data["score"] += 1

            # ✅ Move to next question
            quiz_data["current_question_index"] += 1

        next_question_index = quiz_data["current_question_index"]

        # ✅ Send the next question or finalize the quiz if completed
        if next_question_index < len(saved_quizzes[quiz_id]["questions"]):
            await send_question(bot, quiz_data["chat_id"], quiz_id, next_question_index)
        else:
            await finalize_quiz(bot, quiz_data["chat_id"])

    def check_inactivity(bot, chat_id, quiz_id):
        """Check if the user is inactive and pause the quiz."""
        while True:
            time.sleep(300)  # 5 minutes wait
            with lock:
                if chat_id in active_quizzes:
                    last_activity = active_quizzes[chat_id]["last_activity"]
                    if time.time() - last_activity >= 300:  # 5 minutes of inactivity
                        active_quizzes[chat_id]["paused"] = True
                        bot.send_message(
                            chat_id,
                            "⏸️ **Quiz Paused due to inactivity.**\n\n⚡ *Select any option to continue the test.*",
                            parse_mode="Markdown"
                        )
                        return


    @bot.callback_query_handler(func=lambda call: call.data.startswith("mcq_"))
    async def handle_mcq_selection(call):
        """Handle MCQ selection and auto-resume if paused."""
        chat_id = call.message.chat.id
        quiz_id, selected_option = call.data.split("_", 2)[1:]

        with lock:
            if chat_id in active_quizzes:
                if active_quizzes[chat_id].get("paused"):
                    # ✅ Auto-resume the quiz when user selects an MCQ
                    active_quizzes[chat_id]["paused"] = False
                    active_quizzes[chat_id]["last_activity"] = asyncio.get_event_loop().time()
            
                    remaining_time = active_quizzes[chat_id].get("remaining_time", 0)
                    if remaining_time > 0:
                        asyncio.create_task(quiz_timer(bot, chat_id, quiz_id, remaining_time))
                        active_quizzes[chat_id].pop("remaining_time", None)

        # ✅ Process user's answer and move to the next question
        await process_answer(bot, chat_id, quiz_id, selected_option)
