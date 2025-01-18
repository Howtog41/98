# plugins/start_quiz.py
import threading
import time

active_quizzes = {}

def register_handlers(bot, saved_quizzes, creating_quizzes):
    @bot.message_handler(func=lambda message: message.text.startswith("/start_"))
    def start_quiz(message):
        chat_id = message.chat.id
        quiz_id = message.text.split("_", 1)[1]
        quiz = saved_quizzes.get(quiz_id)
        if not quiz:
            bot.send_message(chat_id, f"No quiz found with ID: {quiz_id}")
            return
        bot.send_message(chat_id, "The quiz is starting now! Good luck!")
        threading.Thread(target=quiz_timer, args=(bot, chat_id, quiz_id, quiz['timer'])).start()
        send_question(bot, chat_id, quiz_id, 0)

    def quiz_timer(bot, chat_id, quiz_id, duration):
        remaining_time = duration
        while remaining_time > 0:
            if remaining_time % 30 == 0 or remaining_time <= 10:
                bot.send_message(chat_id, f"⏳ Time left: {remaining_time} seconds")
            time.sleep(1)
            remaining_time -= 1
        bot.send_message(chat_id, "⏰ Time's up! The quiz has ended.")

    def send_question(bot, chat_id, quiz_id, question_index):
        quiz = saved_quizzes[quiz_id]
        questions = quiz["questions"]
        if question_index >= len(questions):
            bot.send_message(chat_id, "Quiz completed!")
            return
        question = questions[question_index]
        bot.send_poll(
            chat_id,
            question["question"],
            question["options"],
            type="quiz",
            correct_option_id=question["correct_option_id"],
            is_anonymous=False,
            explanation=question["explanation"]
        )
