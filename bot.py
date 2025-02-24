import telebot
import random
import requests
import csv
import io
import re

# ✅ Bot Token
BOT_TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
bot = telebot.TeleBot(BOT_TOKEN)

# ✅ Store Quiz Data { quiz_id: { "form": link, "sheet": link } }
QUIZ_DB = {}

# 🔍 Extract Google Sheet ID from the given link
def extract_sheet_id(sheet_url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    return match.group(1) if match else None

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
    sheet_id = extract_sheet_id(sheet_link)

    if not sheet_id:
        bot.send_message(chat_id, "❌ Invalid Google Sheet link! Please send a correct link.")
        return

    quiz_id = str(random.randint(1000, 9999))  # Unique Quiz ID Generate
    QUIZ_DB[quiz_id] = {"form": form_link, "sheet": sheet_id}

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
    custom_form_link = form_link.replace("YourName", user_name)  # ✅ FIXED

    bot.send_message(chat_id, f"🎯 Click the link below to start the quiz:\n🔗 {custom_form_link}")

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

    sheet_id = QUIZ_DB[quiz_id]["sheet"]
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"

    try:
        response = requests.get(sheet_url)
        response.raise_for_status()
        data = response.text

        # Parse CSV Data
        csv_reader = csv.reader(io.StringIO(data))
        rows = list(csv_reader)  # Convert to List

        if len(rows) < 2:
            bot.send_message(chat_id, "❌ No quiz data found in the sheet!")
            return

        leaderboard_text = "🏆 *Quiz Leaderboard:*\n\n"
        valid_records = []
        total_marks = None  # ✅ Store Total Marks

        for row in rows[1:]:
            try:
                student_name = row[2].strip()  # ✅ Column C (3rd Column) se Name Extract
                score_parts = row[1].split("/")  # ✅ Split "X / Y" Format
                score = int(score_parts[0].strip())  # ✅ Extract Score (X)
                total = int(score_parts[1].strip())  # ✅ Extract Total Marks (Y)

                if total_marks is None:
                    total_marks = total  # ✅ Set Total Marks (first occurrence)

                valid_records.append({"Name": student_name, "Score": score})
            except (ValueError, IndexError):
                continue  # ❌ Ignore Invalid Rows

        if not valid_records:
            bot.send_message(chat_id, "❌ No valid scores found in the sheet!")
            return

        # ✅ Sort Users Based on Score (Descending, Including 0 Scores)
        sorted_records = sorted(valid_records, key=lambda x: x["Score"], reverse=True)

        leaderboard_text += f"📌 *Total Marks:* {total_marks}\n\n"  # ✅ Show Total Marks

        for idx, record in enumerate(sorted_records, 1):  # ✅ Show All Users, Including 0 Scores
            leaderboard_text += f"{idx}. {record['Name']} - {record['Score']} / {total_marks} pts\n"

        bot.send_message(chat_id, leaderboard_text, parse_mode="Markdown")
    
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")
### ✅ Bot Start
bot.polling(none_stop=True)
