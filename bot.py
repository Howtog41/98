from telegram import Update, Poll, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, PollAnswerHandler, ContextTypes
import asyncio
import random

# Bot Token
TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"

# Sample Questions
QUESTIONS = [
    {"question": "What is the capital of France?", "options": ["Paris", "London", "Berlin", "Madrid"], "correct": 0, "explanation": "Paris is the capital of France."},
    {"question": "Which planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Saturn"], "correct": 1, "explanation": "Mars is called the Red Planet due to its iron oxide surface."},
    {"question": "Who wrote 'Hamlet'?", "options": ["Shakespeare", "Hemingway", "Tolstoy", "Orwell"], "correct": 0, "explanation": "William Shakespeare wrote 'Hamlet'."},
]

# Dictionary to track user scores
user_scores = {}
user_active_quiz = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Telegram Quiz Bot! Use /quiz to start the quiz.")

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = 0
    user_active_quiz[user_id] = 0
    await send_next_question(update, context, user_id)

async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if user_active_quiz[user_id] >= len(QUESTIONS):
        await update.message.reply_text(f"Quiz finished! Your final score: {user_scores[user_id]}")
        del user_active_quiz[user_id]
        return
    
    question_data = QUESTIONS[user_active_quiz[user_id]]
    message = await update.message.reply_poll(
        question=question_data["question"],
        options=question_data["options"],
        type=Poll.QUIZ,
        correct_option_id=question_data["correct"],
        explanation=question_data["explanation"],
        is_anonymous=False,
        open_period=10
    )
    context.bot_data[message.poll.id] = {"user_id": user_id, "correct": question_data["correct"], "update": update}
    
    # Schedule next question after open period ends
    await asyncio.sleep(10)
    user_active_quiz[user_id] += 1
    await send_next_question(update, context, user_id)

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id
    
    if poll_id in context.bot_data:
        correct_answer = context.bot_data[poll_id]["correct"]
        update = context.bot_data[poll_id]["update"]
        if poll_answer.option_ids[0] == correct_answer:
            user_scores[user_id] += 1
        user_active_quiz[user_id] += 1
        await send_next_question(update, context, user_id)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_scores:
        await update.message.reply_text("No scores yet!")
        return
    
    leaderboard = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    leaderboard_text = "🏆 Leaderboard:\n"
    for i, (user_id, score) in enumerate(leaderboard[:5], start=1):
        leaderboard_text += f"{i}. User {user_id}: {score} points\n"
    
    await update.message.reply_text(leaderboard_text)

# Setup Application
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", start_quiz))
app.add_handler(CommandHandler("leaderboard", show_leaderboard))
app.add_handler(PollAnswerHandler(handle_poll_answer))

# Run the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
