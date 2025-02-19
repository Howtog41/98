import os
import importlib
from pymongo import MongoClient
from telebot import TeleBot

# Replace with your bot token
BOT_TOKEN = '8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI'
bot = TeleBot(BOT_TOKEN)

# MongoDB connection setup
MONGO_URI = "mongodb+srv://terabox255:h9PjRSpCHsHw5zzt@cluster0.nakwhlt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['mydatabase']  # Replace 'mydatabase' with your database name
quizzes_collection = db['quizzes']  # Collection for storing quizzes

# Load quizzes from MongoDB on startup
saved_quizzes = {}  # To store all quizzes in memory
creating_quizzes = {}  # Temporary in-memory storage for ongoing quizzes
leaderboards = {} 



def fetch_quizzes():
    """
    Load all quizzes from MongoDB into the saved_quizzes dictionary.
    """
    for quiz in quizzes_collection.find():
        saved_quizzes[quiz['quiz_id']] = quiz
        leaderboards[quiz['quiz_id']] = quiz.get('leaderboard', [])
        saved_quizzes[quiz['quiz_id']]["participants"] = quiz.get('participants', 0)
    print(f"Loaded {len(saved_quizzes)} quizzes from MongoDB.")


def save_quiz_to_db(quiz_id, quiz_data):
    """
    Save or update a quiz in MongoDB.
    """
    quizzes_collection.update_one(
        {"quiz_id": quiz_id},  # Filter
        {"$set": {
            "quiz_id": quiz_id,
            "title": quiz_data.get("title", ""),
            "questions": quiz_data.get("questions", []),
            "participants": quiz_data.get("participants", 0),
            "leaderboard": quiz_data.get("leaderboard", []),
            "timer": quiz_data.get("timer"),
            "active": quiz_data.get("active", False)
        }},
        upsert=True  # Insert if not exists
    )

# Dynamically load plugins
def load_plugins():
    plugin_folder = 'plugins'
    for file in os.listdir(plugin_folder):
        if file.endswith('.py') and file != '__init__.py':
            module_name = f"{plugin_folder}.{file[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'register_handlers'):
                module.register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection)

if __name__ == "__main__":
    load_plugins()
    # Load quizzes from MongoDB
    fetch_quizzes()

    print("Bot is running...")
    bot.infinity_polling()
