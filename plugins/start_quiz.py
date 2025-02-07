from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_start_quiz_handlers(bot, saved_quizzes, user_scores):
    @bot.message_handler(commands=['start'])
    def start_command(message):
        """Handle /start command to join quiz or start interaction."""
        chat_id = message.chat.id
        text = message.text

        if text.startswith("/start quiz_"):
            # Extract quiz_id from command
            quiz_id = text.split("_")[1]
            quiz = saved_quizzes.get(quiz_id)

            if not quiz:
                bot.send_message(chat_id, "❌ Quiz not found. Please check the link.")
                return

            # Start the quiz
            bot.send_message(chat_id, f"📋 Starting Quiz: {quiz['title']}\n⏳ Duration: {quiz['timer']} seconds.")
            send_question(chat_id, quiz, 0, user_scores)

        else:
            bot.send_message(chat_id, "Welcome! Use the link provided to start a quiz.")

    def send_question(chat_id, quiz, question_index, user_scores):
        """Send a question to the user."""
        if question_index < len(quiz['questions']):
            question = quiz['questions'][question_index]
            markup = InlineKeyboardMarkup()
            
            for i, option in enumerate(question['options']):
                markup.add(InlineKeyboardButton(option, callback_data=f"answer_{quiz['id']}_{question_index}_{i}"))

            bot.send_message(chat_id, f"Q{question_index + 1}: {question['question']}", reply_markup=markup)
        else:
            # Quiz complete, calculate score
            calculate_score(chat_id, quiz, user_scores)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
    def handle_answer(call):
        """Handle user answers."""
        data = call.data.split("_")
        quiz_id, question_index, selected_option = data[1], int(data[2]), int(data[3])

        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.answer_callback_query(call.id, "Quiz not found.")
            return

        # Store user answer
        chat_id = call.message.chat.id
        user_scores.setdefault(chat_id, {}).setdefault(quiz_id, []).append(selected_option)

        # Send next question
        bot.answer_callback_query(call.id, "Answer recorded!")
        send_question(chat_id, quiz, question_index + 1, user_scores)

    def calculate_score(chat_id, quiz, user_scores):
        """Calculate and send the user's score."""
        answers = user_scores.get(chat_id, {}).get(quiz['id'], [])
        correct_answers = 0

        for i, user_answer in enumerate(answers):
            if quiz['questions'][i]['correct_option_id'] == user_answer:
                correct_answers += 1

        total_questions = len(quiz['questions'])
        bot.send_message(chat_id, f"🎉 Quiz Complete!\nYou scored {correct_answers}/{total_questions}.")

        # Update leaderboard
        update_leaderboard(chat_id, quiz, correct_answers)

    leaderboard = {}

    def update_leaderboard(chat_id, quiz, score):
        """Update the leaderboard for the quiz."""
        quiz_id = quiz['id']
        leaderboard.setdefault(quiz_id, []).append((chat_id, score))
        leaderboard[quiz_id].sort(key=lambda x: x[1], reverse=True)

        # Send leaderboard
        send_leaderboard(chat_id, quiz)

    def send_leaderboard(chat_id, quiz):
        """Send the leaderboard to the user."""
        quiz_id = quiz['id']
        top_scores = leaderboard.get(quiz_id, [])[:10]  # Top 10 scores

        message = f"🏆 Leaderboard for {quiz['title']}:\n"
        for rank, (user_id, score) in enumerate(top_scores, start=1):
            message += f"{rank}. User {user_id}: {score}/{len(quiz['questions'])}\n"

        bot.send_message(chat_id, message)
