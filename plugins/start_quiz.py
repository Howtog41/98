import asyncio
import time
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = AsyncTeleBot("8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI", parse_mode="Markdown")
active_quizzes = {}
saved_quizzes = {}
lock = asyncio.Lock()  # Async lock

async def start_quiz_handler(chat_id, quiz_id):
    """ Start a quiz asynchronously without creating multiple threads """
    async with lock:
        if chat_id in active_quizzes:
            await bot.send_message(chat_id, "You're already in a quiz! Finish it first.")
            return

        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            await bot.send_message(chat_id, "Quiz not found.")
            return

        active_quizzes[chat_id] = {
            "quiz_id": quiz_id,
            "score": 0,
            "current_question_index": 0,
            "end_time": time.time() + quiz["timer"]
        }

    await bot.send_message(chat_id, "🎉 The quiz is starting now! Good luck!")
    asyncio.create_task(quiz_timer(chat_id, quiz["timer"]))  # Run timer in background
    await send_question(chat_id, quiz_id, 0)

async def quiz_timer(chat_id, duration):
    """ Async function to manage quiz time without threads """
    end_time = time.time() + duration

    while time.time() < end_time:
        remaining_time = int(end_time - time.time())

        if remaining_time in [3600, 1800, 900, 600, 300, 60, 30, 10, 5, 3, 1]:
            hours, remainder = divmod(remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
            await bot.send_message(chat_id, f"⏳ Time left: {time_str}")

        await asyncio.sleep(1)  # Async sleep (non-blocking)

    # Auto-submit quiz when time ends
    await bot.send_message(chat_id, "⏰ Time's up! Submitting your quiz...")
    await finalize_quiz(chat_id)

async def send_question(chat_id, quiz_id, question_index):
    """ Async function to send quiz questions """
    quiz = saved_quizzes.get(quiz_id)
    if not quiz or question_index >= len(quiz["questions"]):
        await finalize_quiz(chat_id)
        return

    question = quiz["questions"][question_index]
    numbered_question = f"Q{question_index + 1}: {question['question']}"
    
    await bot.send_poll(
        chat_id=chat_id,
        question=numbered_question,
        options=question["options"],
        type="quiz",
        correct_option_id=question["correct_option_id"],
        is_anonymous=False
    )

async def finalize_quiz(chat_id):
    """ Finalize the quiz asynchronously and update the leaderboard """
    async with lock:
        if chat_id not in active_quizzes:
            await bot.send_message(chat_id, "No active quiz found.")
            return

        quiz_data = active_quizzes.pop(chat_id)
        score = quiz_data["score"]
        quiz_id = quiz_data["quiz_id"]

    leaderboard = saved_quizzes.get(quiz_id, {}).get("leaderboard", [])
    leaderboard.append({"chat_id": chat_id, "score": score})
    leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)

    saved_quizzes[quiz_id]["leaderboard"] = leaderboard
    rank = next((i + 1 for i, entry in enumerate(leaderboard) if entry["chat_id"] == chat_id), len(leaderboard))

    leaderboard_text = f"📊 Quiz Completed! Your Score: {score}\n🏅 Rank: {rank}/{len(leaderboard)}\n"
    await bot.send_message(chat_id, leaderboard_text)
