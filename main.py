import os
import importlib
from telebot import TeleBot
from pymongo import MongoClient
# Replace with your bot token
BOT_TOKEN = '8151017957:AAEhEOxbwjnw6Fxu1GzPwHTVhUeIpibpJqI'
bot = TeleBot(BOT_TOKEN)
MONGO_URI = "mongodb+srv://latestkoreandraama:UjebJR51Dki7Ili2@cluster0.nnnuejc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['quiz_bot']

saved_quizzes = db['quizzes'] # To store all quizzes
creating_quizzes = db['sessions']

# Dynamically load plugins
def load_plugins():
    plugin_folder = 'plugins'
    for file in os.listdir(plugin_folder):
        if file.endswith('.py') and file != '__init__.py':
            module_name = f"{plugin_folder}.{file[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'register_handlers'):
                module.register_handlers(bot, saved_quizzes, creating_quizzes)

if __name__ == "__main__":
    load_plugins()
    print("Bot is running...")
    bot.infinity_polling()
