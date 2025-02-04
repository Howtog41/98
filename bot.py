import telebot
import threading
import random
import string
import time
from pymongo import MongoClient

# Dictionary to keep track of active timers
active_timers = {}

# Telegram Bot Token
BOT_TOKEN = '8151017957:AAEhEOxbwjnw6Fxu1GzPwHTVhUeIpibpJqI'
bot = telebot.TeleBot(BOT_TOKEN)

# MongoDB connection
MONGO_URI = "mongodb+srv://latestkoreandraama:UjebJR51Dki7Ili2@cluster0.nnnuejc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['quiz_bot']

# MongoDB Collections
quizzes_collection = db['quizzes']
sessions_collection = db['sessions']
leaderboard_collection = db['leaderboards']

# Generate a unique quiz ID
def generate_quiz_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# Command to start creating a quiz
@bot.message_handler(commands=['create_quiz'])
def create_quiz(message):
    chat_id = message.chat.id

    # Prevent multiple quizzes from being created at once
    if quizzes_collection.find_one({"chat_id": chat_id, "status": "creating"}):
        bot.send_message(chat_id, "You're already creating a quiz. Complete it or use /cancel_quiz to start over.")
        return

    quizzes_collection.insert_one({
        "chat_id": chat_id,
        "title": None,
        "questions": [],
        "timer": None,
        "quiz_id": generate_quiz_id(),
        "status": "creating"
    })
    bot.send_message(chat_id, "Please send the quiz title.")

# Set the quiz title
@bot.message_handler(func=lambda message: quizzes_collection.find_one({"chat_id": message.chat.id, "status": "creating", "title": None}))
def set_quiz_title(message):
    chat_id = message.chat.id
    quizzes_collection.update_one(
        {"chat_id": chat_id, "status": "creating"},
        {"$set": {"title": message.text}}
    )
    bot.send_message(chat_id, "Quiz title saved! Now forward polls from your channel to add them to the quiz.\nType /done when you're finished.")

# Handle forwarded polls
@bot.message_handler(content_types=['poll'])
def handle_forwarded_poll(message):
    chat_id = message.chat.id
    quiz = quizzes_collection.find_one({"chat_id": chat_id, "status": "creating"})

    if not quiz:
        bot.send_message(chat_id, "You are not currently creating a quiz. Use /create_quiz to start.")
        return

    poll = message.poll
    quizzes_collection.update_one(
        {"chat_id": chat_id, "status": "creating"},
        {"$push": {"questions": {
            "question": poll.question,
            "options": [option.text for option in poll.options],
            "correct_option_id": poll.correct_option_id,
            "explanation": poll.explanation or "No explanation provided."
        }}}
    )
    bot.send_message(chat_id, f"Poll added: {poll.question}\nSend another poll or type /done to finish.")

# Finish quiz creation
@bot.message_handler(commands=['done'])
def finish_quiz_creation(message):
    chat_id = message.chat.id
    quiz = quizzes_collection.find_one({"chat_id": chat_id, "status": "creating"})

    if not quiz or not quiz.get("questions"):
        bot.send_message(chat_id, "You haven't created any quiz or added any questions. Use /create_quiz to start.")
        return

    bot.send_message(chat_id, "Quiz creation complete! Please send the quiz duration in seconds (e.g., 180 for 3 minutes).")
    quizzes_collection.update_one({"chat_id": chat_id, "status": "creating"}, {"$set": {"status": "awaiting_timer"}})

# Set the quiz timer
@bot.message_handler(func=lambda message: quizzes_collection.find_one({"chat_id": message.chat.id, "status": "awaiting_timer"}))
def set_quiz_timer(message):
    chat_id = message.chat.id
    try:
        timer = int(message.text)
        if timer <= 0:
            raise ValueError

        quiz = quizzes_collection.find_one({"chat_id": chat_id, "status": "awaiting_timer"})
        quizzes_collection.update_one(
            {"chat_id": chat_id, "status": "awaiting_timer"},
            {"$set": {"timer": timer, "status": "ready"}}
        )

        bot.send_message(chat_id, f"Quiz created successfully! \ud83c\udf89\nQuiz ID: {quiz['quiz_id']}\nUse /view_quizzes to see all quizzes.")
    except ValueError:
        bot.send_message(chat_id, "Invalid input. Please send a valid number of seconds.")

# View available quizzes
@bot.message_handler(commands=['view_quizzes'])
def view_quizzes(message):
    chat_id = message.chat.id
    count = quizzes_collection.count_documents({"chat_id": chat_id, "status": "ready"})

    if count == 0:
        bot.send_message(chat_id, "No quizzes available.")
        return

    quizzes = quizzes_collection.find({"chat_id": chat_id, "status": "ready"})
    response = "Your Quizzes:\n\n"
    for quiz in quizzes:
        title = quiz["title"]
        questions_count = len(quiz["questions"])
        response += f"{title} \ud83d\udd8b\ufe0f {questions_count} Questions\nStart: /start_{quiz['quiz_id']}\n\n"

    bot.send_message(chat_id, response)

# Start a quiz
@bot.message_handler(func=lambda message: message.text.startswith("/start_"))
def start_quiz(message):
    chat_id = message.chat.id
    quiz_id = message.text.split("_", 1)[1]
    quiz = quizzes_collection.find_one({"quiz_id": quiz_id, "status": "ready"})

    if not quiz:
        bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
        return

    sessions_collection.insert_one({
        "chat_id": chat_id,
        "quiz_id": quiz_id,
        "current_question": 0,
        "score": 0,
        "unanswered": [],
        "status": "active"
    })

    bot.send_message(chat_id, "The quiz is starting now! Good luck!")
    start_timer(chat_id, quiz_id, quiz["timer"])
    send_question(chat_id, quiz_id, 0)

# Start the quiz timer
def start_timer(chat_id, quiz_id, duration):
    timer_thread = threading.Thread(target=quiz_timer, args=(chat_id, quiz_id, duration))
    timer_thread.daemon = True
    active_timers[chat_id] = timer_thread
    timer_thread.start()

# Handle the quiz timer
def quiz_timer(chat_id, quiz_id, duration):
    for remaining_time in range(duration, 0, -1):
        session = sessions_collection.find_one({"chat_id": chat_id, "quiz_id": quiz_id, "status": "active"})
        if not session:
            return

        if remaining_time % 30 == 0 or remaining_time <= 10:
            bot.send_message(chat_id, f"\u23f3 Time left: {remaining_time} seconds")
        time.sleep(1)

    bot.send_message(chat_id, "\u23f0 Time's up! The quiz has ended.")
    finish_quiz(chat_id)
    active_timers.pop(chat_id, None)

# Send a question to the user
def send_question(chat_id, quiz_id, question_index):
    quiz = quizzes_collection.find_one({"quiz_id": quiz_id, "status": "ready"})
    questions = quiz["questions"]

    if question_index >= len(questions):
        finish_quiz(chat_id)
        return

    question = questions[question_index]
    sessions_collection.update_one(
        {"chat_id": chat_id, "quiz_id": quiz_id, "status": "active"},
        {"$set": {"current_question": question_index}}
    )

    bot.send_poll(
        chat_id,
        question["question"],
        question["options"],
        type="quiz",
        correct_option_id=question["correct_option_id"],
        is_anonymous=False,
        explanation=question["explanation"]
    )

# Handle poll answers
@bot.poll_answer_handler(func=lambda poll_answer: True)
def handle_poll_answer(poll_answer):
    chat_id = poll_answer.user.id
    session = sessions_collection.find_one({"chat_id": chat_id, "status": "active"})

    if not session:
        return

    quiz_id = session["quiz_id"]
    current_question = session["current_question"]
    quiz = quizzes_collection.find_one({"quiz_id": quiz_id})

    if poll_answer.option_ids[0] == quiz["questions"][current_question]["correct_option_id"]:
        sessions_collection.update_one(
            {"chat_id": chat_id, "quiz_id": quiz_id, "status": "active"},
            {"$inc": {"score": 1}}
        )
    else:
        sessions_collection.update_one(
            {"chat_id": chat_id, "quiz_id": quiz_id, "status": "active"},
            {"$push": {"unanswered": quiz["questions"][current_question]["question"]}}
        )

    send_question(chat_id, quiz_id, current_question + 1)

# Finish the quiz
def finish_quiz(chat_id):
    session = sessions_collection.find_one({"chat_id": chat_id, "status": "active"})

    if not session:
        return

    quiz_id = session["quiz_id"]
    score = session["score"]
    unanswered = session.get("unanswered", [])

    bot.send_message(chat_id, f"Quiz completed! 🎉\nYour score: {score}")

    # Update the leaderboard
    leaderboard_collection.update_one(
        {"quiz_id": quiz_id},
        {"$push": {"scores": {"user_id": chat_id, "score": score}}},
        upsert=True
    )

    # Show the leaderboard
    show_leaderboard(chat_id, quiz_id)

    # Offer to view unanswered questions
    if unanswered:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("View Unanswered", callback_data=f"view_unanswered_{quiz_id}"))
        bot.send_message(chat_id, "You left some questions unanswered. Click below to review them.", reply_markup=markup)

    # Clean up the session
    sessions_collection.delete_one({"chat_id": chat_id, "status": "active"})

# Show leaderboard
def show_leaderboard(chat_id, quiz_id):
    leaderboard = leaderboard_collection.find_one({"quiz_id": quiz_id})
    if not leaderboard or not leaderboard.get("scores"):
        bot.send_message(chat_id, "No leaderboard data available.")
        return

    # Sort scores in descending order and handle ties
    sorted_scores = sorted(leaderboard["scores"], key=lambda x: x["score"], reverse=True)
    response = f"🏆 Leaderboard for Quiz {quiz_id}:\n\n"
    rank = 1
    previous_score = None

    for i, entry in enumerate(sorted_scores):
        # Assign rank only if the score is different from the previous score
        if previous_score != entry["score"]:
            rank = i + 1

        user_id = entry["user_id"]
        user_info = bot.get_chat(user_id)  # Fetch user details for a better display
        user_name = user_info.username or user_info.first_name or "User"

        response += f"{rank}. {user_name}: {entry['score']} points\n"
        previous_score = entry["score"]

    bot.send_message(chat_id, response)

# Callback handler for viewing unanswered questions
@bot.callback_query_handler(func=lambda call: call.data.startswith("view_unanswered_"))
def view_unanswered_questions(call):
    quiz_id = call.data.split("_", 2)[2]
    session = sessions_collection.find_one({"chat_id": call.message.chat.id, "quiz_id": quiz_id, "status": "finished"})

    if not session or not session.get("unanswered"):
        bot.answer_callback_query(call.id, "No unanswered questions to display.")
        return

    unanswered = session["unanswered"]
    response = "🔍 Unanswered Questions:\n\n" + "\n".join(unanswered)
    bot.send_message(call.message.chat.id, response)


# Run the bot
bot.infinity_polling()
