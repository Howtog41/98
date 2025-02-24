import telebot
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Bot Token
BOT_TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
bot = telebot.TeleBot(BOT_TOKEN)

# ✅ Google Sheets API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# ✅ Store Quiz Data { quiz_id: { "form": link, "sheet": link } }
QUIZ_DB = {}

### 🟢 1️⃣ Command: Register Quiz (/form_quiz)
@bot.message_handler(commands=['form_quiz'])
def register_quiz(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📌 Send the Google Form link:")
    bot.register_next_step_handler(message, get_form_link, chat_id)

def get_form_link(message, chat_id):
    form_link = message.text
    bot.send_message(chat_id, "📌 Now send the Google Sheet (Responses) link:")
    bot.register_next_step_handler(message, get_sheet_link, chat_id, form_link)

def get_sheet_link(message, chat_id, form_link):
    sheet_link = message.text
    quiz_id = str(random.randint(1000, 9999))  # Unique Quiz ID Generate

    QUIZ_DB[quiz_id] = {"form": form_link, "sheet": sheet_link}
    
    bot.send_message(chat_id, f"✅ Quiz Registered!\n\n📌 *Quiz ID:* `{quiz_id}`\n🔗 Use `/start_quiz {quiz_id}` to share with users!", parse_mode="Markdown")

### 🟢 2️⃣ Command: Start Quiz (/start_quiz)
@bot.message_handler(commands=['start_quiz'])
def start_quiz(message):
    chat_id = message.chat.id
    msg_parts = message.text.split()
    
    if len(msg_parts) < 2:
        bot.send_message(chat_id, "❌ Please provide a valid Quiz ID! Example: `/start_quiz 1234`")
        return
    
    quiz_id = msg_parts[1]
    
    if quiz_id not in QUIZ_DB:
        bot.send_message(chat_id, "❌ Invalid Quiz ID! Please check and try again.")
        return

    form_link = QUIZ_DB[quiz_id]["form"]
    
    # Extract Telegram Name
    user_name = message.from_user.first_name
    custom_form_link = f"{form_link}&entry.YOUR_FIELD_ID={user_name}"  # Replace YOUR_FIELD_ID with actual field ID
    
    bot.send_message(chat_id, f"🎯 Click the link below to start the quiz:\n🔗 {custom_form_link}")

### 🟢 3️⃣ Command: Get Leaderboard (/leaderboard)
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    chat_id = message.chat.id
    msg_parts = message.text.split()

    if len(msg_parts) < 2:
        bot.send_message(chat_id, "❌ Please provide a valid Quiz ID! Example: `/leaderboard 1234`")
        return

    quiz_id = msg_parts[1]

    if quiz_id not in QUIZ_DB:
        bot.send_message(chat_id, "❌ Invalid Quiz ID!")
        return

    sheet_link = QUIZ_DB[quiz_id]["sheet"]
    sheet_id = sheet_link.split("/d/")[1].split("/")[0]  # Extract Sheet ID

    try:
        # Open Google Sheet
        sheet = client.open_by_key(sheet_id).sheet1
        records = sheet.get_all_records()

        leaderboard_text = "🏆 *Leaderboard:*\n\n"
        sorted_records = sorted(records, key=lambda x: x["Score"], reverse=True)[:10]  # Sort Top 10

        for idx, record in enumerate(sorted_records, 1):
            leaderboard_text += f"{idx}. {record['Name']} - {record['Score']} pts\n"

        bot.send_message(chat_id, leaderboard_text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")

### ✅ Bot Start
bot.polling(none_stop=True)
