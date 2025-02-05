from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
def register_handlers(bot, saved_quizzes, creating_quizzes):
    QUIZZES_PER_PAGE = 10

    @bot.message_handler(commands=['view_quizzes'])
    def view_quizzes(message, page=1):
        """Display paginated list of quiz titles and unique IDs."""
        chat_id = message.chat.id
        quiz_list = list(saved_quizzes.items())
        total_quizzes = len(quiz_list)
        total_pages = (total_quizzes + QUIZZES_PER_PAGE - 1) // QUIZZES_PER_PAGE

        if total_quizzes == 0:
            bot.send_message(chat_id, "No quizzes available.")
            return

        start_index = (page - 1) * QUIZZES_PER_PAGE
        end_index = start_index + QUIZZES_PER_PAGE
        quizzes_to_display = quiz_list[start_index:end_index]

        markup = InlineKeyboardMarkup()
        for quiz_id, quiz in quizzes_to_display:
            markup.add(InlineKeyboardButton(f"{quiz['title']} ({quiz_id})", callback_data=f"view_quiz_{quiz_id}"))

        # Add pagination buttons
        if page > 1:
            markup.add(InlineKeyboardButton("⬅️ Previous", callback_data=f"view_page_{page - 1}"))
        if page < total_pages:
            markup.add(InlineKeyboardButton("➡️ Next", callback_data=f"view_page_{page + 1}"))

        bot.send_message(
            chat_id,
            f"📋 **Saved Quizzes (Page {page}/{total_pages})**\n\n"
            "Click on a quiz to view options.",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_page_"))
    def paginate_quizzes(call):
        """Handle pagination for the quiz list."""
        page = int(call.data.split("_")[2])
        bot.delete_message(call.message.chat.id, call.message.message_id)
        view_quizzes(call.message, page)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_quiz_"))
    def view_quiz_options(call):
        """Display options for a specific quiz."""
        quiz_id = call.data.split("_")[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.answer_callback_query(call.id, "Quiz not found.")
            return

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✏️ Edit Quiz", callback_data=f"edit_quiz_{quiz_id}"),
            InlineKeyboardButton("🔗 Share Quiz", callback_data=f"share_quiz_{quiz_id}")
        )
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="view_quizzes_1"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"📋 **Quiz Title**: {quiz['title']}\n"
                f"🆔 **Quiz ID**: {quiz_id}\n"
                f"📝 **Questions**: {len(quiz['questions'])}\n"
                f"⏳ **Duration**: {quiz['timer']} seconds\n\n"
                "Choose an option below:"
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_quiz_"))
    def edit_quiz(call):
        """Edit options for the selected quiz."""
        quiz_id = call.data.split("_")[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.answer_callback_query(call.id, "Quiz not found.")
            return

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✏️ Edit Title", callback_data=f"edit_title_{quiz_id}"),
            InlineKeyboardButton("📄 Edit Questions", callback_data=f"edit_questions_{quiz_id}"),
            InlineKeyboardButton("⏳ Edit Timer", callback_data=f"edit_timer_{quiz_id}")
        )
        markup.row(InlineKeyboardButton("🔙 Back", callback_data=f"view_quiz_{quiz_id}"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"📋 **Editing Quiz**: {quiz['title']}\n\n"
                f"Choose an option to edit:"
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("share_quiz_"))
    def share_quiz(call):
        """Generate a shareable link for the quiz."""
        quiz_id = call.data.split("_")[2]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.answer_callback_query(call.id, "Quiz not found.")
            return

        bot_username = bot.get_me().username
        share_link = f"https://t.me/{bot_username}?start=quiz_{quiz_id}"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Back", callback_data=f"view_quiz_{quiz_id}"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"🔗 **Shareable Link for Quiz**: {quiz['title']}\n\n"
                f"📍 [Click here to take the quiz!]({share_link})"
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )
