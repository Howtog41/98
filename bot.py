from telegram import Update, Poll, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, PollAnswerHandler, ContextTypes, CallbackContext
import asyncio
import random
import logging
from pymongo import MongoClient
import os

# Configure Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Bot Token
TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
MONGO_URI = "mongodb+srv://terabox255:h9PjRSpCHsHw5zzt@cluster0.nakwhlt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB
db_client = MongoClient(MONGO_URI)
db = db_client["quiz_bot"]
user_scores = db["user_scores"]

# Sample Questions
QUESTIONS = [
    {"question": "What is the capital of France?", "options": ["Paris", "London", "Berlin", "Madrid"], "correct": 0, "explanation": "Paris is the capital of France."},
    {"question": "Which planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Saturn"], "correct": 1, "explanation": "Mars is called the Red Planet due to its iron oxide surface."},
    {"question": "Who wrote 'Hamlet'?", "options": ["Shakespeare", "Hemingway", "Tolstoy", "Orwell"], "correct": 0, "explanation": "William Shakespeare wrote 'Hamlet'."},
]

user_active_quiz = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Telegram Quiz Bot! Use /quiz to start the quiz.")

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_scores.update_one({"user_id": user_id}, {"$setOnInsert": {"score": 0}}, upsert=True)
    user_active_quiz[user_id] = 0
    await send_next_question(update, context, user_id)

async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if user_active_quiz[user_id] >= len(QUESTIONS):
        await show_leaderboard(update, context)
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

        # Ensure user is in active quiz state
        if user_id not in user_active_quiz:
            user_active_quiz[user_id] = 0  # Initialize user progress
        
        if poll_answer.option_ids[0] == correct_answer:
            user_scores.update_one({"user_id": user_id}, {"$inc": {"score": 1}})
        
        user_active_quiz[user_id] += 1
        await send_next_question(update, context, user_id)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard = user_scores.find().sort("score", -1).limit(5)
    leaderboard_text = "🏆 Leaderboard:\n"
    for i, user in enumerate(leaderboard, start=1):
        leaderboard_text += f"{i}. User {user['user_id']}: {user['score']} points\n"
    
    if not leaderboard_text.strip():
        await update.message.reply_text("No scores yet!")
    else:
        await update.message.reply_text(leaderboard_text)

# Setup Application
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", start_quiz))
app.add_handler(CommandHandler("leaderboard", show_leaderboard))
app.add_handler(PollAnswerHandler(handle_poll_answer))

# Run the bot with Webhook
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
