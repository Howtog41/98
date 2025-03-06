import os
import importlib
import asyncio
from pymongo import MongoClient
from aiogram import Bot, Dispatcher, types
from aiogram import Bot, Dispatcher

# Bot Token
BOT_TOKEN = '8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI'  # ✅ अपना टोकन डालें

# Aiogram Bot और Dispatcher सेटअप
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# MongoDB connection setup
MONGO_URI = "mongodb+srv://terabox255:h9PjRSpCHsHw5zzt@cluster0.nakwhlt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # ✅ Mongo URI डालें
client = MongoClient(MONGO_URI)
db = client['mydatabase']  # ✅ अपनी डेटाबेस का नाम डालें
quizzes_collection = db['quizzes']

# In-memory storage
saved_quizzes = {}
creating_quizzes = {}
leaderboards = {}


async def fetch_quizzes():
    """
    Load all quizzes from MongoDB asynchronously.
    """
    global saved_quizzes, leaderboards
    saved_quizzes.clear()
    leaderboards.clear()

    async for quiz in quizzes_collection.find({}):
        saved_quizzes[quiz['quiz_id']] = quiz
        leaderboards[quiz['quiz_id']] = quiz.get('leaderboard', [])
        saved_quizzes[quiz['quiz_id']]["participants"] = quiz.get('participants', 0)

    print(f"Loaded {len(saved_quizzes)} quizzes from MongoDB.")


async def save_quiz_to_db(quiz_id, quiz_data):
    """
    Save or update a quiz in MongoDB asynchronously.
    """
    await quizzes_collection.update_one(
        {"quiz_id": quiz_id},
        {"$set": {
            "quiz_id": quiz_id,
            "title": quiz_data.get("title", ""),
            "questions": quiz_data.get("questions", []),
            "participants": quiz_data.get("participants", 0),
            "leaderboard": quiz_data.get("leaderboard", []),
            "timer": quiz_data.get("timer"),
            "active": quiz_data.get("active", False)
        }},
        upsert=True
    )


def load_plugins():
    """
    Dynamically load all plugins.
    """
    plugin_folder = 'plugins'
    for file in os.listdir(plugin_folder):
        if file.endswith('.py') and file != '__init__.py':
            module_name = f"{plugin_folder}.{file[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'register_handlers'):
                module.register_handlers(dp, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection)


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    """
    Handle the /start command.
    """
    await message.answer("Welcome! Use the commands to interact with me.")


async def main():
    """
    Main function to start the bot.
    """
    load_plugins()
    await fetch_quizzes()
    print("Bot is running...")
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
