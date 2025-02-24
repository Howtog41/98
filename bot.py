import telebot
import random
import requests
import csv
import io
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# Replace with your MongoDB connection string
MONGO_URI = "mongodb+srv://terabox255:h9PjRSpCHsHw5zzt@cluster0.nakwhlt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  
client = MongoClient(MONGO_URI)
db = client["quiz_bot_db"]  # Database Name
quiz_collection = db["quizzes"]  # Collection for storing quiz details
rank_collection = db["rankings"]  # Collection for storing user ranks

# ✅ Bot Token
BOT_TOKEN = "8151017957:AAF15t0POw7oHaFjC-AySwvDmNyS3tZxbTI"
bot = telebot.TeleBot(BOT_TOKEN)

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
    # Store in MongoDB
    quiz_collection.insert_one({
        "quiz_id": quiz_id,
        "title": quiz_title,
        "form": form_link,
        "sheet": sheet_id
    })
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
    quiz = quiz_collection.find_one({"quiz_id": quiz_id})
    if not quiz:
        bot.send_message(chat_id, "❌ Quiz not found! Please check the link and try again.")
        return

    quiz_title = quiz["title"]
    form_link = quiz["form"]

    # ✅ Extract Telegram User ID & Generate Prefilled Link
    user_id = str(message.from_user.id)  # Convert to string for URL
    custom_form_link = form_link.replace("YourName", user_id)  

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("rank_"))
def show_rank(call):
    chat_id = call.message.chat.id
    quiz_id = call.data.replace("rank_", "")
    user_id = call.from_user.id  # ✅ Store Current User ID
    quiz = quiz_collection.find_one({"quiz_id": quiz_id})
    if not quiz:
        bot.answer_callback_query(call.id, "❌ Quiz not found!", show_alert=True)
        return

    sheet_id = quiz["sheet"]
    
    # Check if user rank is already in MongoDB
    user_rank_data = rank_collection.find_one({"quiz_id": quiz_id, "user_id": user_id})
    if user_rank_data:
        rank_text = (
            f"📌 <b>Your Rank:</b> {user_rank_data['rank']}/{user_rank_data['total_users']}\n"
            f"📊 <b>Your Score:</b> {user_rank_data['score']}/{user_rank_data['total_marks']}\n\n"
        )
        bot.send_message(chat_id, rank_text, parse_mode="HTML")
        return
        
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"

    try:
        response = requests.get(sheet_url)
        response.raise_for_status()
        data = response.text

        # ✅ Parse CSV Data
        csv_reader = csv.reader(io.StringIO(data))
        rows = list(csv_reader)

        if len(rows) < 2:
            bot.send_message(chat_id, "❌ No quiz data found in the sheet!")
            return

        valid_records = {}
        total_marks = None
        user_score = None
        user_rank = None
        user_attempted = False  # ✅ Track if user attempted test

        for row in rows[1:]:  # Skip Header
            try:
                if len(row) < 3:
                    continue  # ❌ Skip invalid rows

                student_id = int(row[2].strip())  # ✅ Column C (3rd Column) → User ID
                score_parts = row[1].strip().split("/")  # ✅ Column B (2nd Column) → "X / Y" Format

                if len(score_parts) != 2:
                    continue  # ❌ Skip invalid score format

                score = int(score_parts[0].strip())  # ✅ Extract Score
                total = int(score_parts[1].strip())  # ✅ Extract Total Marks

                if total_marks is None:
                    total_marks = total  # ✅ Set Total Marks

                # ✅ Ignore Duplicate Attempts, Keep Only First Entry
                if student_id not in valid_records:
                    valid_records[student_id] = score

                # ✅ Track if user attempted test
                if student_id == user_id:
                    user_attempted = True

            except (ValueError, IndexError) as e:
                print(f"Skipping invalid row: {row} | Error: {e}")  # 🔍 Debugging

        if not valid_records:
            bot.send_message(chat_id, "❌ No valid scores found in the sheet! Check format.")
            return

        # ✅ Sort Users Based on Score (Descending)
        sorted_records = sorted(valid_records.items(), key=lambda x: x[1], reverse=True)

        # 🔹 Find User Rank
        for idx, (uid, score) in enumerate(sorted_records, 1):
            if uid == user_id:
                user_rank = idx
                user_score = score

        # ✅ If user did not attempt the test
        if not user_attempted:
            bot.send_message(chat_id, "❌ Aapne yeh test attend nahi kiya hai ya aapne apne predefined roll number ko badal diya hai!")
            return
            
        # Store user rank in MongoDB for future reference
        rank_collection.insert_one({
            "quiz_id": quiz_id,
            "user_id": user_id,
            "rank": user_rank,
            "score": user_score,
            "total_marks": total_marks,
            "total_users": len(sorted_records)
        })
        
        # ✅ Display User Rank & Top 5 Leaderboard
        rank_text = f"📌 <b>Your Rank:</b> {user_rank}/{len(sorted_records)}\n"
        rank_text += f"📊 <b>Your Score:</b> {user_score}/{total_marks}\n\n"
        rank_text += "<b>🏅 Top 5 Players:</b>\n"

        for idx, (uid, score) in enumerate(sorted_records[:5], 1):
            try:
                user_info = bot.get_chat(uid)  # ✅ Directly fetch user data
                print(f"User Info for {uid}: {user_info}")  # 🔍 Debugging Output

                first_name = user_info.first_name if user_info.first_name else ""
                last_name = user_info.last_name if user_info.last_name else ""
                username = f"@{user_info.username}" if user_info.username else ""

                if first_name or last_name:
                    user_name = f"{first_name} {last_name}".strip()  # ✅ Prefer full name
                elif username:
                    user_name = username  # ✅ Use username if no name
                else:
                    user_name = "Unknown"  # ❌ Fallback if nothing found

            except Exception as e:
                print(f"Error fetching user info for {uid}: {e}")  # 🔍 Debugging
                user_name = "Unknown"

            rank_text += f"{idx}. {user_name} - {score} pts\n"


        # ✅ Send Message without any Markdown Errors
        bot.send_message(chat_id, rank_text, parse_mode="HTML")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error fetching leaderboard: {e}")

### ✅ Bot Start
bot.polling(none_stop=True)
