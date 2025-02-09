import os
import importlib
from pymongo import MongoClient
from telebot import TeleBot

# Replace with your bot token
BOT_TOKEN = '8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI'
bot = TeleBot(BOT_TOKEN)

# MongoDB connection setup
MONGO_URI = "mongodb+srv://terabox255:WGDvo991VYvLAm5w@cluster0.1gfjb8w.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['mydatabase']  # Replace 'mydatabase' with your database name
quizzes_collection = db['quizzes']  # Collection for storing quizzes


def save_quiz_to_db(quiz_data):
    """
    Save or update a quiz in MongoDB.
    """
    try:
        quizzes_collection.update_one(
            {"quiz_id": quiz_data['quiz_id']},  # Filter based on quiz_id
            {"$set": quiz_data},  # Update or insert quiz data
            upsert=True  # Insert if not found
        )
        print(f"Quiz saved to DB: {quiz_data['quiz_id']}")
    except Exception as e:
        print(f"Error saving quiz: {e}")


def fetch_quiz_from_db(quiz_id):
    """
    Fetch a single quiz from MongoDB using quiz_id.
    """
    try:
        quiz = quizzes_collection.find_one({"quiz_id": quiz_id})
        if quiz:
            print(f"Quiz fetched: {quiz_id}")
            return quiz
        else:
            print(f"No quiz found with ID: {quiz_id}")
            return None
    except Exception as e:
        print(f"Error fetching quiz: {e}")
        return None


@bot.message_handler(commands=['new_quiz'])
def new_quiz(message):
    """
    Example of creating a new quiz and saving it to MongoDB.
    """
    quiz_data = {
        "quiz_id": "quiz123",  # Replace with dynamic ID generation
        "title": "Sample Quiz",
        "questions": [
            {"question": "What is 2+2?", "options": ["3", "4", "5"], "answer": "4"}
        ]
    }
    save_quiz_to_db(quiz_data)
    bot.reply_to(message, "Quiz saved to the database!")


@bot.message_handler(commands=['get_quiz'])
def get_quiz(message):
    """
    Example of fetching a quiz from MongoDB.
    """
    quiz_id = "quiz123"  # Replace with dynamic user input
    quiz = fetch_quiz_from_db(quiz_id)
    if quiz:
        bot.reply_to(message, f"Quiz Title: {quiz['title']}\nQuestions: {len(quiz['questions'])}")
    else:
        bot.reply_to(message, "Quiz not found!")


# Dynamically load plugins (if required)
def load_plugins():
    plugin_folder = 'plugins'
    for file in os.listdir(plugin_folder):
        if file.endswith('.py') and file != '__init__.py':
            module_name = f"{plugin_folder}.{file[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'register_handlers'):
                module.register_handlers(bot, save_quiz_to_db, fetch_quiz_from_db)


if __name__ == "__main__":
    load_plugins()
    print("Bot is running...")
    bot.infinity_polling()
