from telegram import Update, Poll, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, PollAnswerHandler, ContextTypes, CallbackContext
import asyncio
import random
import logging
import psycopg2
import os

# Configure Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Bot Token
TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
DATABASE_URL = "mongodb+srv://terabox255:h9PjRSpCHsHw5zzt@cluster0.nakwhlt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to PostgreSQL Database
def connect_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Create Table for User Scores
def setup_database():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_scores (
            user_id BIGINT PRIMARY KEY,
            score INT DEFAULT 0
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Sample Questions
QUESTIONS = [
    {"question": "What is the capital of France?", "options": ["Paris", "London", "Berlin", "Madrid"], "correct": 0, "explanation": "Paris is the capital of France."},
    {"question": "Which planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Saturn"], "correct": 1, "explanation": "Mars is called the Red Planet due to its iron oxide surface."},
    {"question": "Who wrote 'Hamlet'?", "options": ["Shakespeare", "Hemingway", "Tolstoy", "Orwell"], "correct": 0, "explanation": "William Shakespeare wrote 'Hamlet'."},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Telegram Quiz Bot! Use /quiz to start the quiz.")

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_scores (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    await send_next_question(update, context, user_id)

async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    question_data = random.choice(QUESTIONS)
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
    await send_next_question(update, context, user_id)

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id
    
    if poll_id in context.bot_data:
        correct_answer = context.bot_data[poll_id]["correct"]
        update = context.bot_data[poll_id]["update"]
        if poll_answer.option_ids[0] == correct_answer:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE user_scores SET score = score + 1 WHERE user_id = %s", (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
        await send_next_question(update, context, user_id)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, score FROM user_scores ORDER BY score DESC LIMIT 5")
    leaderboard = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not leaderboard:
        await update.message.reply_text("No scores yet!")
        return
    
    leaderboard_text = "🏆 Leaderboard:\n"
    for i, (user_id, score) in enumerate(leaderboard, start=1):
        leaderboard_text += f"{i}. User {user_id}: {score} points\n"
    
    await update.message.reply_text(leaderboard_text)

# Setup Application
setup_database()
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", start_quiz))
app.add_handler(CommandHandler("leaderboard", show_leaderboard))
app.add_handler(PollAnswerHandler(handle_poll_answer))

# Run the bot with Webhook
if __name__ == "__main__":
    print("Bot is running...")
    app.run_webhook(listen="0.0.0.0", port=int(os.environ.get("PORT", 8443)), url_path=TOKEN)
