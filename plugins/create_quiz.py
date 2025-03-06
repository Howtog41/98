import random
import string
from aiogram import types, Dispatcher


def generate_quiz_id():
    """Generate a unique quiz ID."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def register_handlers(dp: Dispatcher, saved_quizzes, creating_quizzes, save_quiz_to_db, quizzes_collection):
    @dp.message_handler(commands=['create_quiz'])
    async def create_quiz(message: types.Message):
        """Start creating a new quiz."""
        chat_id = message.chat.id
        creating_quizzes[chat_id] = {
            "title": None,
            "questions": [],
            "current_pre_poll_message": None,
            "timer": None,
            "active": True
        }
        await message.answer("Please send the quiz title.")

    @dp.message_handler(lambda message: message.chat.id in creating_quizzes and creating_quizzes[message.chat.id]["active"] and not creating_quizzes[message.chat.id]["title"])
    async def set_quiz_title(message: types.Message):
        """Set the title for the quiz."""
        chat_id = message.chat.id
        creating_quizzes[chat_id]["title"] = message.text
        await message.answer(
            "Quiz title saved! 🎉\nNow send a pre-poll message (optional) for the next poll.\n"
            "If you don't want to add a pre-poll message, simply forward the poll.\n"
            "Type /done when you're finished.\n"
            "If you sent a pre-poll message by mistake, use /undo to reset it."
        )

    @dp.message_handler(commands=['undo'])
    async def undo_pre_poll_message(message: types.Message):
        """Undo the last pre-poll message."""
        chat_id = message.chat.id
        if chat_id in creating_quizzes and creating_quizzes[chat_id]["active"] and creating_quizzes[chat_id]["current_pre_poll_message"]:
            creating_quizzes[chat_id]["current_pre_poll_message"] = None
            await message.answer("Pre-poll message cleared! 🎉 Now you can send a new one or forward the poll.")
        else:
            await message.answer("No pre-poll message to undo.")

    @dp.message_handler(lambda message: message.chat.id in creating_quizzes and creating_quizzes[message.chat.id]["active"] and creating_quizzes[message.chat.id]["title"], content_types=['text', 'photo', 'video'])
    async def set_individual_pre_poll_message(message: types.Message):
        """Set a pre-poll message for the next poll."""
        chat_id = message.chat.id
        if message.content_type == 'text':
            creating_quizzes[chat_id]["current_pre_poll_message"] = {"type": "text", "content": message.text}
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            creating_quizzes[chat_id]["current_pre_poll_message"] = {"type": "photo", "content": file_id}
        elif message.content_type == 'video':
            file_id = message.video.file_id
            creating_quizzes[chat_id]["current_pre_poll_message"] = {"type": "video", "content": file_id}

        await message.answer(
            "Pre-poll message saved! 🎉 Now forward the poll this message applies to.\n"
            "If you sent this message by mistake, use /undo to reset it."
        )

    def validate_correct_option_id(options, correct_option_id):
        if 0 <= correct_option_id < len(options):
            return correct_option_id
        else:
            raise ValueError(f"Invalid correct_option_id: {correct_option_id}. Options: {options}")

    @dp.message_handler(content_types=['poll'])
    async def handle_forwarded_poll(message: types.Message):
        """Add a forwarded poll to the quiz, along with its pre-poll message."""
        chat_id = message.chat.id
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id]["active"] or not creating_quizzes[chat_id].get("title"):
            await message.answer("You are not currently creating a quiz. Use /create_quiz to start.")
            return

        poll = message.poll
        pre_poll_message = creating_quizzes[chat_id]["current_pre_poll_message"]

        creating_quizzes[chat_id]["questions"].append({
            "pre_poll_message": pre_poll_message,
            "question": poll.question,
            "options": [opt.text for opt in poll.options],
            "correct_option_id": validate_correct_option_id([opt.text for opt in poll.options], poll.correct_option_id),
            "explanation": poll.explanation or "No explanation provided."
        })

        creating_quizzes[chat_id]["current_pre_poll_message"] = None

        await message.answer(
            f"Poll added: {poll.question}\nSend another pre-poll message (optional) or forward another poll.\n"
            "Type /done when you're finished."
        )

    @dp.message_handler(commands=['done'])
    async def finish_quiz_creation(message: types.Message):
        """Complete the quiz creation process and ask for the timer."""
        chat_id = message.chat.id
        if chat_id not in creating_quizzes or not creating_quizzes[chat_id]["active"] or not creating_quizzes[chat_id]["questions"]:
            await message.answer("No questions added. Use /create_quiz to start again.")
            return

        creating_quizzes[chat_id]["active"] = False
        await message.answer("Quiz creation complete! 🎉 Now, send the quiz duration in seconds (e.g., 120 for 2 minutes).")

    @dp.message_handler(lambda message: message.chat.id in creating_quizzes and not creating_quizzes[message.chat.id]["active"] and creating_quizzes[message.chat.id]["timer"] is None)
    async def set_quiz_timer(message: types.Message):
        """Set the timer for the quiz."""
        chat_id = message.chat.id
        try:
            timer = int(message.text)
            if timer <= 0:
                raise ValueError
            creating_quizzes[chat_id]["timer"] = timer
            quiz_id = generate_quiz_id()

            quiz_data = creating_quizzes.pop(chat_id)
            quiz_data["quiz_id"] = quiz_id  
            quiz_data["participants"] = 0  
            quiz_data["leaderboard"] = {}  
            quiz_data["active"] = False  

            await save_quiz_to_db(quiz_id, quiz_data)
            saved_quizzes[quiz_id] = quiz_data
            await message.answer(f"Quiz created successfully! 🎉\nQuiz ID: {quiz_id}\nUse /view_quizzes to see all quizzes.")
        except ValueError:
            await message.answer("Invalid duration. Please send the duration in seconds (e.g., 120 for 2 minutes).")
