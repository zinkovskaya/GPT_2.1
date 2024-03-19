import logging

import telebot
from dotenv import load_dotenv
from telebot.types import Message
from telebot.types import ReplyKeyboardMarkup

import db
from config import ADMINS, LOGS_PATH, MAX_TASK_TOKENS, TOKEN
from gpt import ask_gpt_helper, count_tokens

logging.basicConfig(
    filename=LOGS_PATH,
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
    filemode="w",
)

load_dotenv()
bot = telebot.TeleBot(TOKEN)

db.create_db()
db.create_table()

subjects_list = [
    "Математика",
    "Физика",
    "Химия",
    "Информатика",
    "Русский язык",
    "Английский язык"
]
levels_list = ["Новичок", "Продвинутый", "Профессионал"]


@bot.message_handler(commands=["start"])  # обработка комманды start
def start(message):
    user_name = message.from_user.first_name
    user_id = message.from_user.id

    if not db.is_user_in_db(user_id):  # проверка пользователя в базе данных
        db.add_new_user((user_id, None, None, None, None))

    bot.send_message(
        user_id,
        f"Приветствую тебя, {user_name}!\n" 
        f"Привет, {user_name}! Я бот-помощник для решения задач по разным предметам!\n"
        f"Ты можешь выбрать предмет и сложность, написать условие задачи, а я постараюсь её решить.\n"
        f"Иногда ответы получаются слишком длинными - в этом случае ты можешь попросить продолжить.",
        reply_markup=create_keyboard(["Выбрать предмет"]),
    )
    bot.register_next_step_handler(message, choose_subject)


def filter_choose_subject(message: Message) -> bool:
    return message.text in ["Выбрать предмет", "Выбрать другой предмет"]


@bot.message_handler(func=filter_choose_subject)
def choose_subject(message: Message):
    bot.send_message(
        message.from_user.id,
        "Выбери предмет, по которому тебе нужна помощь:",
        reply_markup=create_keyboard(subjects_list),
    )
    bot.register_next_step_handler(message, subject_selection)


def subject_selection(message: Message):
    user_id = message.from_user.id
    user_answer = message.text
    if user_answer in subjects_list:  # проверка предмета
        db.update_row(user_id, "subject", user_answer)
        bot.send_message(
            user_id,
            f"Отлично, {message.from_user.first_name}, теперь я буду помогать тебе по предмету '{user_answer}'!"
            f"Давай теперь выберем сложность моих ответов по этому предмету.",
            reply_markup=create_keyboard(levels_list),
        )
        bot.register_next_step_handler(message, level_selection)

    else:
        bot.send_message(
            user_id,
            "К сожалению, по такому предмету я не смогу тебе помочь, выбери один из предложенных в меню",
            reply_markup=create_keyboard(subjects_list),
        )
        bot.register_next_step_handler(message, subject_selection)


def filter_choose_level(message: Message):
    return message.text == "Изменить сложность ответов"


@bot.message_handler(func=filter_choose_level)
def choose_level(message: Message):
    bot.send_message(
        message.from_user.id,
        "Какой уровень сложности ответов тебе нужен:",
        reply_markup=create_keyboard(levels_list),
    )
    bot.register_next_step_handler(message, level_selection)


def level_selection(message: Message):  # функция для выбора уровня
    user_id = message.from_user.id
    user_answer = message.text
    if user_answer in levels_list:  # проверка введенного значения
        db.update_row(user_id, "level", user_answer)
        bot.send_message(
            user_id,
            f"Принято, {message.from_user.first_name}! Теперь мои ответы будут сложности: '{user_answer}'. "
            f"А теперь задай свой вопрос",
        )
        bot.register_next_step_handler(message, give_answer)
    else:
        bot.send_message(
            user_id,
            "Пожалуйста, выбери сложность из предложенных:",
            reply_markup=create_keyboard(levels_list),
        )
        bot.register_next_step_handler(message, level_selection)


def filter_solve_task(message: Message) -> bool:
    return message.text == "Задать новый вопрос"


@bot.message_handler(func=filter_solve_task)
def solve_task(message):
    bot.send_message(message.from_user.id, "Напиши условие задачи:")
    bot.register_next_step_handler(message, give_answer)


def give_answer(message: Message):  # функция отправки ответа от gpt
    user_id = message.from_user.id
    user_task = message.text
    subject = db.get_user_data(user_id)["subject"]
    level = db.get_user_data(user_id)["level"]

    if count_tokens(user_task) <= MAX_TASK_TOKENS:  # проверка задачи на токены
        bot.send_message(message.from_user.id, "Решаю...")
        answer = ask_gpt_helper(user_task, subject, level)
        db.update_row(user_id, "task", user_task)
        db.update_row(user_id, "answer", answer)

        if answer is None:  # обработка ошибки от gpt
            bot.send_message(
                user_id,
                "Не могу получить ответ от GPT :(",
                reply_markup=create_keyboard(
                    [
                        "Задать новый вопрос",
                        "Выбрать другой предмет",
                        "Изменить сложность ответов",
                    ]
                ),
            )
        elif answer == "":  # если нет ответа
            bot.send_message(
                user_id,
                "Не могу сформулировать решение :(",
                reply_markup=create_keyboard(
                    [
                        "Задать новый вопрос",
                        "Выбрать другой предмет",
                        "Изменить сложность ответов",
                    ]
                ),
            )
            logging.info(
                f"Отправлено: {message.text}\nПолучена ошибка: нейросеть вернула пустую строку"
            )
        else:  # все ок
            bot.send_message(
                user_id,
                answer,
                reply_markup=create_keyboard(
                    [
                        "Задать новый вопрос",
                        "Продолжить объяснение",
                        "Выбрать другой предмет",
                        "Изменить сложность ответов",
                    ]
                ),
            )

    else:   # если токенов много

        db.update_row(user_id, "task", None)
        db.update_row(user_id, "answer", None)

        bot.send_message(
            message.from_user.id,
            "Текст задачи слишком длинный. Пожалуйста, попробуй его укоротить.",
        )
        logging.info(
            f"Отправлено: {message.text}\nПолучено: Текст задачи слишком длинный"
        )
        bot.register_next_step_handler(message, give_answer)


def filter_continue_explaining(message: Message) -> bool:
    return message.text == "Продолжить объяснение"


@bot.message_handler(func=filter_continue_explaining)
def continue_explaining(message):  # фунция продолжения объяснения
    user_id = message.from_user.id
    current_task = db.get_user_data(user_id)["task"]
    current_answer = db.get_user_data(user_id)["answer"]
    subject = db.get_user_data(user_id)["subject"]
    level = db.get_user_data(user_id)["level"]

    if not current_task:
        bot.send_message(
            user_id,
            "Для начала напиши условие задачи:",
            reply_markup=create_keyboard(["Задать новый вопрос"]),
        )
    else:
        bot.send_message(user_id, "Формулирую продолжение...")
        answer = ask_gpt_helper(current_task, subject, level, current_answer)
        current_answer += answer
        db.update_row(user_id, "answer", current_answer)

        if answer is None:
            bot.send_message(
                user_id,
                "Не могу получить ответ от GPT :(",
                reply_markup=create_keyboard(
                    [
                        "Задать новый вопрос",
                        "Выбрать другой предмет",
                        "Изменить сложность ответов",
                    ]
                ),
            )
        elif answer == "":
            bot.send_message(
                user_id,
                "Задача полностью решена ^-^",
                reply_markup=create_keyboard(
                    [
                        "Задать новый вопрос",
                        "Выбрать другой предмет",
                        "Изменить сложность ответов",
                    ]
                ),
            )
        else:
            bot.send_message(
                user_id,
                answer,
                reply_markup=create_keyboard(
                    [
                        "Задать новый вопрос",
                        "Продолжить объяснение",
                        "Выбрать другой предмет",
                        "Изменить сложность ответов",
                    ]
                ),
            )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.from_user.id, text="Я твой цифровой собеседник. "
                                                "Узнать обо мне подробнее можно командой /about")


@bot.message_handler(commands=['about'])
def about_command(message):
    bot.send_message(message.from_user.id, text="Рад, что ты заинтересован_а! Мое предназначение — "
                                                "не оставлять тебя в одиночестве и всячески подбадривать!\n"
                                                "Я помогу тебе с твоим вопросом, тебе просто нужно выбрать предмет "
                                                "(математика/русский/…), уровня объяснения (как новичку/как профи/…).")


@bot.message_handler(commands=["debug"])
def send_logs(message):
    user_id = message.from_user.id
    with open(LOGS_PATH, "rb") as f:
        if user_id in ADMINS:
            bot.send_document(message.from_user.id, f)


def create_keyboard(buttons: list[str]) -> ReplyKeyboardMarkup:  # создание кнопок
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons)
    return keyboard


bot.polling()
