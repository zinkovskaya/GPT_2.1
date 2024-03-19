import logging

import requests
from transformers import AutoTokenizer

from config import GPT_URL, LOGS_PATH, MAX_TASK_TOKENS, MODEL_NAME

logging.basicConfig(
    filename=LOGS_PATH,
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
    filemode="w",
)


def count_tokens(text: str) -> int:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return len(tokenizer.encode(text))


def ask_gpt_helper(task, subject, level, previous_answer=""):

    system_content = (
        f"Ты учитель по предмету {subject}. Формулируй ответы уровня {level}"
    )
    assistant_content = "Решим задачу по шагам: " + previous_answer
    temperature = 1
    max_tokens = 64

    response = requests.post(
        GPT_URL,
        headers={"Content-Type": "application/json"},
        json={
            "messages": [
                {"role": "user", "content": task},
                {"role": "system", "content": system_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )
    if response.status_code == 200:
        result = response.json()["choices"][0]["message"]["content"]
        print("Ответ получен!")
        logging.debug(f"Отправлено: {task}\nПолучен результат: {result}")
        return result
    else:
        print("Не удалось получить ответ :(")
        logging.error(f"Отправлено: {task}\nПолучена ошибка: {response.json()}")
