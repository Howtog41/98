import os
import importlib
from telebot import TeleBot

# Replace with your bot token
BOT_TOKEN = '7646738501:AAFzHOOyPfJcE_3t4fjwGSd1FKhqwa4hcOo'
bot = TeleBot(BOT_TOKEN)

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
