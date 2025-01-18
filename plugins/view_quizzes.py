from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_handlers(bot, saved_quizzes, creating_quizzes):
    @bot.message_handler(commands=['view_quizzes'])
    def view_quizzes(message):
        """Display all saved quizzes with options to edit or share."""
        chat_id = message.chat.id
        if not saved_quizzes:
            bot.send_message(chat_id, "No quizzes available.")
            return
        
        for quiz_id, quiz in saved_quizzes.items():
            markup = InlineKeyboardMarkup()
            # Add buttons for edit and share
            markup.row(
                InlineKeyboardButton("✏️ Edit Quiz", callback_data=f"edit_quiz_{quiz_id}"),
                InlineKeyboardButton("🔗 Share Quiz", callback_data=f"share_quiz_{quiz_id}")
            )
            response = (
                f"📋 **Quiz Title**: {quiz['title']}\n"
                f"📝 **Questions**: {len(quiz['questions'])}\n"
                f"⏳ **Duration**: {quiz['timer']} seconds\n"
            )
            bot.send_message(chat_id, response, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_quiz_"))
    def edit_quiz(call):
        """Allow the user to edit an existing quiz."""
        quiz_id = call.data.split("_", 2)[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.answer_callback_query(call.id, "Quiz not found.")
            return
        
        # Send quiz details for editing
        bot.send_message(
            call.message.chat.id,
            f"Editing Quiz: **{quiz['title']}**\n\n"
            f"1️⃣ **Title**: {quiz['title']}\n"
            f"2️⃣ **Questions**: {len(quiz['questions'])}\n"
            f"3️⃣ **Duration**: {quiz['timer']} seconds\n\n"
            f"Send a command to edit:\n"
            f"/edit_title_{quiz_id} - Edit Title\n"
            f"/edit_questions_{quiz_id} - Edit Questions\n"
            f"/edit_timer_{quiz_id} - Edit Timer",
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("share_quiz_"))
    def share_quiz(call):
        """Generate a shareable link for the quiz."""
        quiz_id = call.data.split("_", 2)[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.answer_callback_query(call.id, "Quiz not found.")
            return
        
        # Generate a shareable link (placeholder for actual implementation)
        share_link = f"https://your-quiz-platform.com/quiz/{quiz_id}"  # Replace with actual URL structure
        bot.send_message(
            call.message.chat.id,
            f"🔗 **Shareable Link for Quiz**: {quiz['title']}\n\n"
            f"📍 [Click here to take the quiz!]({share_link})",
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: message.text.startswith("/edit_title_"))
    def edit_quiz_title(message):
        """Edit the title of the quiz."""
        quiz_id = message.text.split("_", 2)[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(message.chat.id, "Quiz not found.")
            return
        
        bot.send_message(message.chat.id, "Send the new title for the quiz.")
        bot.register_next_step_handler(message, lambda msg: save_new_title(msg, quiz_id))

    def save_new_title(message, quiz_id):
        """Save the new title for the quiz."""
        new_title = message.text
        saved_quizzes[quiz_id]["title"] = new_title
        bot.send_message(message.chat.id, f"Quiz title updated to: **{new_title}**", parse_mode="Markdown")

    @bot.message_handler(func=lambda message: message.text.startswith("/edit_questions_"))
    def edit_quiz_questions(message):
        """Edit the questions in the quiz."""
        quiz_id = message.text.split("_", 2)[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(message.chat.id, "Quiz not found.")
            return
        
        bot.send_message(
            message.chat.id,
            "Current questions:\n\n" +
            "\n".join([f"{i+1}. {q['question']}" for i, q in enumerate(quiz["questions"])]) +
            "\n\nSend a new poll to replace the questions, or use /add_question_{quiz_id} to add more."
        )

    @bot.message_handler(func=lambda message: message.text.startswith("/edit_timer_"))
    def edit_quiz_timer(message):
        """Edit the timer of the quiz."""
        quiz_id = message.text.split("_", 2)[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(message.chat.id, "Quiz not found.")
            return
        
        bot.send_message(message.chat.id, "Send the new timer in seconds.")
        bot.register_next_step_handler(message, lambda msg: save_new_timer(msg, quiz_id))

    def save_new_timer(message, quiz_id):
        """Save the new timer for the quiz."""
        try:
            new_timer = int(message.text)
            if new_timer <= 0:
                raise ValueError
            saved_quizzes[quiz_id]["timer"] = new_timer
            bot.send_message(message.chat.id, f"Quiz timer updated to: **{new_timer} seconds**", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "Invalid timer. Please send a positive number.")
