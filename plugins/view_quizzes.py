from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_handlers(bot, saved_quizzes):
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

        # Update the current message instead of sending a new one
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✏️ Edit Title", callback_data=f"edit_title_{quiz_id}"),
            InlineKeyboardButton("📄 Edit Questions", callback_data=f"edit_questions_{quiz_id}"),
            InlineKeyboardButton("⏳ Edit Timer", callback_data=f"edit_timer_{quiz_id}")
        )
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="view_quizzes"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"📋 **Editing Quiz**: {quiz['title']}\n\n"
                f"📝 **Questions**: {len(quiz['questions'])}\n"
                f"⏳ **Timer**: {quiz['timer']} seconds\n\n"
                f"Choose an option to edit:"
            ),
            reply_markup=markup,
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

        # Generate a bot-specific shareable link
        bot_username = bot.get_me().username
        share_link = f"https://t.me/{bot_username}?start={quiz_id}"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"🔗 **Shareable Link for Quiz**: {quiz['title']}\n\n"
                f"📍 [Click here to take the quiz!]({share_link})"
            ),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "view_quizzes")
    def back_to_view(call):
        """Go back to the list of quizzes."""
        bot.delete_message(call.message.chat.id, call.message.message_id)
        view_quizzes(call.message)
