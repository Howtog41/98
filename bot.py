import telebot
import random
import requests
import csv
import io
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ✅ Bot Token
BOT_TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
bot = telebot.TeleBot(BOT_TOKEN)

# ✅ Store Quiz Data { quiz_id: { "title": title, "form": link, "sheet": link } }
QUIZ_DB = {}

# 🔍 Extract Google Sheet ID from the given link
def extract_sheet_id(sheet_url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    return match.group(1) if match else None

# 🔍 Extract Google Form Title from the HTML Content
def extract_form_title(form_url):
    try:
        response = requests.get(form_url)
        response.raise_for_status()
        title_match = re.search(r"<title>(.*?)</title>", response.text)
        return title_match.group(1) if title_match else "Quiz"
    except:
        return "Quiz"

### 🟢 1️⃣ Command: Register Quiz (/form_quiz)
@bot.message_handler(commands=['form_quiz'])
def register_quiz(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📌 Send the Google Form link:")
    bot.register_next_step_handler(message, get_form_link, chat_id)

def get_form_link(message, chat_id):
    form_link = message.text
    quiz_title = extract_form_title(form_link)  # ✅ Extract Form Title
    bot.send_message(chat_id, "📌 Now send the Google Sheet (Responses) link:")
    bot.register_next_step_handler(message, get_sheet_link, chat_id, form_link, quiz_title)

def get_sheet_link(message, chat_id, form_link, quiz_title):
    sheet_link = message.text
    sheet_id = extract_sheet_id(sheet_link)

    if not sheet_id:
        bot.send_message(chat_id, "❌ Invalid Google Sheet link! Please send a correct link.")
        return

    quiz_id = str(random.randint(1000, 9999))  # Unique Quiz ID Generate
    QUIZ_DB[quiz_id] = {"title": quiz_title, "form": form_link, "sheet": sheet_id}

    shareable_link = f"https://t.me/{bot.get_me().username}?start=quiz_{quiz_id}"

    bot.send_message(chat_id, f"✅ Quiz Registered!\n<b>Quiz ID:</b> <code>{quiz_id}</code>\n📢 Share this link:\n<a href='{shareable_link}'>Click Here</a>", parse_mode="HTML")

@bot.message_handler(commands=['start'])
def start_quiz_from_link(message):
    chat_id = message.chat.id
    msg_parts = message.text.split()

    if len(msg_parts) < 2 or not msg_parts[1].startswith("quiz_"):
        bot.send_message(chat_id, "❌ Invalid Quiz Link! Please use a valid shared link.")
        return

    quiz_id = msg_parts[1].replace("quiz_", "")

    if quiz_id not in QUIZ_DB:
        bot.send_message(chat_id, "❌ Quiz not found! Please check the link and try again.")
        return

    quiz_title = QUIZ_DB[quiz_id]["title"]
    form_link = QUIZ_DB[quiz_id]["form"]

    # ✅ Extract Telegram Name & Generate Prefilled Link
    user_name = message.from_user.first_name or "User"
    custom_form_link = form_link.replace("YourName", user_name)  

    # ✅ Inline Keyboard for Start Test & Your Rank
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🟢 Start Test", url=custom_form_link),
        InlineKeyboardButton("📊 Your Rank", callback_data=f"rank_{quiz_id}")
    )

    bot.send_message(
        chat_id,
        f"📌 *{quiz_title}*\n\nClick below to start the test or check your rank.",
        parse_mode="Markdown",
        reply_markup=markup
    )
### 🟢 3️⃣ Handle "Your Rank" Button Click
@bot.callback_query_handler(func=lambda call: call.data.startswith("rank_"))
def show_rank(call):
    chat_id = call.message.chat.id
    quiz_id = call.data.replace("rank_", "")

    if quiz_id not in QUIZ_DB:
        bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
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
        user_score = None
        user_rank = None
        user_name = call.from_user.first_name

        for row in rows[1:]:
            try:
                student_name = row[2].strip()  # ✅ Column C (3rd Column) se Name Extract
                score_parts = row[1].split("/")  # ✅ Split "X / Y" Format
                score = int(score_parts[0].strip())  # ✅ Extract Score (X)
                total = int(score_parts[1].strip())  # ✅ Extract Total Marks (Y)

                if total_marks is None:
                    total_marks = total  # ✅ Set Total Marks (first occurrence)

                valid_records.append({"Name": student_name, "Score": score})

                if student_name.lower() == user_name.lower():
                    user_score = score

            except (ValueError, IndexError):
                continue  # ❌ Ignore Invalid Rows

        if not valid_records:
            bot.send_message(chat_id, "❌ No valid scores found in the sheet!")
            return

        # ✅ Sort Users Based on Score (Descending)
        sorted_records = sorted(valid_records, key=lambda x: x["Score"], reverse=True)

        # 🔹 Find User Rank
        for idx, record in enumerate(sorted_records, 1):
            if record["Name"].lower() == user_name.lower():
                user_rank = idx

        # ✅ Display User Rank & Top 5 Leaderboard
        rank_text = f"📌 *Your Rank:* {user_rank}/{len(sorted_records)}\n📊 *Your Score:* {user_score}/{total_marks}\n\n"
        rank_text += "🏅 *Top 5 Players:*\n"

        for idx, record in enumerate(sorted_records[:5], 1):
            rank_text += f"{idx}. {record['Name']} - {record['Score']} pts\n"

        bot.send_message(chat_id, rank_text, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")

### ✅ Bot Start
bot.polling(none_stop=True)
