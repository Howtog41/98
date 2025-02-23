from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_quiz_handlers(bot, saved_quizzes, user_quiz_sessions):
    
    @bot.message_handler(commands=['start_quiz'])
    def start_quiz(message):
        """Ask the user if they are ready to start the quiz."""
        chat_id = message.chat.id

        # Check if any quiz exists
        if not saved_quizzes:
            bot.send_message(chat_id, "No quizzes are available at the moment.")
            return
        
        # Get the first quiz (You can modify to select a specific quiz)
        quiz_id, quiz_data = next(iter(saved_quizzes.items()))
        
        # Save user session
        user_quiz_sessions[chat_id] = {
            "quiz_id": quiz_id,
            "current_question": 0,
            "score": 0,
            "answers": {}
        }

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("I'm Ready ✅", callback_data=f"start_quiz_{quiz_id}"))
        
        bot.send_message(chat_id, "Are you ready for this quiz?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_quiz_"))
    def start_actual_quiz(call):
        """Start the quiz when user clicks 'I'm Ready'."""
        chat_id = call.message.chat.id
        quiz_id = call.data.split("_")[-1]

        # Remove the "I'm Ready" button
        bot.edit_message_text("Quiz started! 🎯 Get ready for the first question.", chat_id, call.message.message_id)

        send_next_question(bot, chat_id)

    def send_next_question(bot, chat_id):
        """Send the next question in the quiz."""
        if chat_id not in user_quiz_sessions:
            return
        
        session = user_quiz_sessions[chat_id]
        quiz_id = session["quiz_id"]
        question_index = session["current_question"]

        if question_index >= len(saved_quizzes[quiz_id]["questions"]):
            # Quiz finished
            send_leaderboard(bot, chat_id)
            return

        question_data = saved_quizzes[quiz_id]["questions"][question_index]

        # Send pre-poll message (if available)
        if question_data.get("pre_poll_message"):
            msg_type = question_data["pre_poll_message"]["type"]
            content = question_data["pre_poll_message"]["content"]

            if msg_type == "text":
                bot.send_message(chat_id, content)
            elif msg_type == "photo":
                bot.send_photo(chat_id, content)
            elif msg_type == "video":
                bot.send_video(chat_id, content)

        # Send actual poll question
        poll_message = bot.send_poll(
            chat_id,
            question_data["question"],
            question_data["options"],
            type="quiz",
            correct_option_id=question_data["correct_option_id"],
            explanation=question_data["explanation"],
            open_period=saved_quizzes[quiz_id]["questions"][question_index].get("open_period", 30)
        )

        # Save the poll message ID for tracking
        session["current_poll_id"] = poll_message.poll.id

    @bot.poll_answer_handler()
    def handle_poll_answer(poll_answer):
        """Handle user responses to quiz questions."""
        chat_id = poll_answer.user.id

        if chat_id not in user_quiz_sessions:
            return
        
        session = user_quiz_sessions[chat_id]
        quiz_id = session["quiz_id"]
        question_index = session["current_question"]

        correct_option_id = saved_quizzes[quiz_id]["questions"][question_index]["correct_option_id"]

        # Check if the answer is correct
        if poll_answer.option_ids[0] == correct_option_id:
            session["score"] += 1

        session["answers"][question_index] = poll_answer.option_ids[0]
        session["current_question"] += 1

        # Send next question
        send_next_question(bot, chat_id)

    def send_leaderboard(bot, chat_id):
        """Show the leaderboard when quiz ends."""
        session = user_quiz_sessions.pop(chat_id, None)
        if not session:
            return

        score = session["score"]
        total_questions = len(saved_quizzes[session["quiz_id"]]["questions"])

        bot.send_message(chat_id, f"🎉 Quiz Completed!\n\nYour Score: {score}/{total_questions}\n")
