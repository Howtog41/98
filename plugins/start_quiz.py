import asyncio
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

active_quizzes = {}
saved_quizzes = {}
leaderboards = {}

def register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection):
    global db_collection
    db_collection = quizzes_collection
    
    @bot.message_handler(commands=["start"])
    async def start_handler(message):
        chat_id = message.chat.id
        if len(message.text.split()) > 1:
            param = message.text.split()[1]
            if param.startswith("quiz_"):
                quiz_id = param.split("_", 1)[1]
                await ask_user_ready(bot, chat_id, quiz_id)
            else:
                await bot.send_message(chat_id, "Invalid parameter. Please check the link.")
        else:
            await bot.send_message(chat_id, "Welcome! Use the commands to interact with me.")

    async def ask_user_ready(bot, chat_id, quiz_id):
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            await bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return

        title = quiz["title"]
        timer = quiz["timer"]
        minutes, seconds = divmod(timer, 60)
        time_str = f"{minutes} min {seconds} sec"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("I'm Ready", callback_data=f"start_quiz_{quiz_id}"))
        await bot.send_message(
            chat_id,
            f"📝 **Quiz Title:** {title}\n⏳ **Duration:** {time_str}\n\n🎉 **Are you ready to begin?**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_quiz_"))
    async def handle_start_quiz(call):
        quiz_id = call.data.split("_", 2)[2]
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        await bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        await start_quiz_handler(bot, chat_id, quiz_id)

    async def start_quiz_handler(bot, chat_id, quiz_id):
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            await bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return

        if chat_id in active_quizzes:
            await bot.send_message(chat_id, "You're already in a quiz! Finish it first before starting a new one.")
            return

        active_quizzes[chat_id] = {
            "quiz_id": quiz_id,
            "score": 0,
            "current_question_index": 0,
            "end_time": time.time() + quiz["timer"]
        }

        await bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        asyncio.create_task(quiz_timer(bot, chat_id, quiz_id, quiz["timer"]))
        await send_question(bot, chat_id, quiz_id, 0)

    async def quiz_timer(bot, chat_id, quiz_id, duration):
        end_time = time.time() + duration
        time_alerts = {3600, 1800, 900, 600, 300, 60, 30, 10, 5}
        while time.time() < end_time:
            remaining_time = int(end_time - time.time())
            if remaining_time in time_alerts:
                await bot.send_message(chat_id, f"⏳ Time left: {remaining_time // 60} min {remaining_time % 60} sec")
            await asyncio.sleep(5)

        if chat_id in active_quizzes:
            await bot.send_message(chat_id, "⏰ Time's up! The quiz has ended.")
            await finalize_quiz(bot, chat_id)

    async def send_question(bot, chat_id, quiz_id, question_index):
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            await bot.send_message(chat_id, "Quiz not found.")
            return

        questions = quiz["questions"]
        if question_index >= len(questions):
            await finalize_quiz(bot, chat_id)
            return

        question = questions[question_index]
        numbered_question = f"Q{question_index + 1}/{len(questions)}: {question['question']}"
        
        await bot.send_poll(
            chat_id=chat_id,
            question=numbered_question,
            options=question["options"],
            type="quiz",
            correct_option_id=question["correct_option_id"],
            is_anonymous=False
        )

    async def finalize_quiz(bot, chat_id):
        if chat_id not in active_quizzes:
            await bot.send_message(chat_id, "No active quiz found.")
            return

        quiz_data = active_quizzes.pop(chat_id)
        score = quiz_data["score"]
        quiz_id = quiz_data["quiz_id"]

        quiz = db_collection.find_one({"quiz_id": quiz_id})
        if not quiz:
            await bot.send_message(chat_id, "Error: Quiz not found in database.")
            return

        leaderboard = quiz.get("leaderboard", [])
        leaderboard.append({"chat_id": chat_id, "score": score})
        leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)

        db_collection.update_one(
            {"quiz_id": quiz_id},
            {"$set": {"leaderboard": leaderboard, "participants": len(leaderboard)}}
        )

        rank = next((i + 1 for i, entry in enumerate(leaderboard) if entry["chat_id"] == chat_id), len(leaderboard))
        leaderboard_text = f"🎉 Your Score: {score}\n🏅 Your Rank: {rank}/{len(leaderboard)}"
        await bot.send_message(chat_id, leaderboard_text)

    @bot.poll_answer_handler()
    async def handle_poll_answer(poll_answer):
        user_id = poll_answer.user.id
        if user_id not in active_quizzes:
            return

        quiz_data = active_quizzes[user_id]
        quiz_id = quiz_data["quiz_id"]
        question_index = quiz_data["current_question_index"]

        if poll_answer.option_ids[0] == saved_quizzes[quiz_id]["questions"][question_index]["correct_option_id"]:
            quiz_data["score"] += 1
        
        quiz_data["current_question_index"] += 1
        next_question_index = quiz_data["current_question_index"]

        if next_question_index < len(saved_quizzes[quiz_id]["questions"]):
            await send_question(bot, quiz_data["chat_id"], quiz_id, next_question_index)
        else:
            await finalize_quiz(bot, quiz_data["chat_id"])
