import os
import importlib

from telebot import TeleBot

# Replace with your bot token
BOT_TOKEN = '8151017957:AAEhEOxbwjnw6Fxu1GzPwHTVhUeIpibpJqI'
bot = TeleBot(BOT_TOKEN)


# Load quizzes from MongoDB on startup
saved_quizzes = {}  # To store all quizzes in memory
creating_quizzes = {}  # Temporary in-memory storage for ongoing quizzes



# Dynamically load plugins
def load_plugins():
    plugin_folder = 'plugins'
    for file in os.listdir(plugin_folder):
        if file.endswith('.py') and file != '__init__.py':
            module_name = f"{plugin_folder}.{file[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, 'register_handlers'):
                module.register_handlers(bot, saved_quizzes, creating_quizzes, save_quiz_to_db)

if __name__ == "__main__":
    # Load quizzes from MongoDB
    fetch_quizzes()

    print("Bot is running...")
    bot.infinity_polling()
