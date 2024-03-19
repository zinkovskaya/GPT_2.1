import sqlite3

from config import DB_NAME, DB_TABLE_USERS_NAME


def create_db():  # функция создания базы данных
    connection = sqlite3.connect(DB_NAME)
    connection.close()


def execute_query(query: str, data: tuple | None = None, db_name: str = DB_NAME):  # функция отправки комманд в бд
    try:
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()

        if data:
            cursor.execute(query, data)
            connection.commit()

        else:
            cursor.execute(query)

    except sqlite3.Error as e:
        print("Ошибка при выполнении запроса: ", e)

    else:
        result = cursor.fetchall()
        connection.close()
        return result


def create_table():  # функция создания таблицы
    sql_query = (
        f"CREATE TABLE IF NOT EXISTS {DB_TABLE_USERS_NAME} "
        f"(id INTEGER PRIMARY KEY, "
        f"user_id INTEGER, "
        f"subject TEXT, "
        f"level TEXT, "
        f"task TEXT, "
        f"answer TEXT);"
    )

    execute_query(sql_query)
    print("Таблица успешно создана")


def add_new_user(user_data: tuple):  # функция добавления нового позьзователя в таблицу
    if not is_user_in_db(user_data[0]):
        columns = "(user_id, subject, level, task, answer)"
        sql_query = (
            f"INSERT INTO {DB_TABLE_USERS_NAME} "
            f"{columns}"
            f"VALUES (?, ?, ?, ?, ?);"
        )

        execute_query(sql_query, user_data)
        print("Пользователь успешно добавлен")
    else:
        print("Пользователь уже существует!")


def is_user_in_db(user_id: int) -> bool:  # функция проверки пользователя в таблице
    sql_query = f"SELECT user_id " f"FROM {DB_TABLE_USERS_NAME} " f"WHERE user_id = ?;"
    return bool(execute_query(sql_query, (user_id,)))


def update_row(user_id: int, column_name: str, new_value: str | None):  # функция изменения данных пользователя
    if is_user_in_db(user_id):
        sql_query = (
            f"UPDATE {DB_TABLE_USERS_NAME} "
            f"SET {column_name} = ? "
            f"WHERE user_id = ?;"
        )

        execute_query(sql_query, (new_value, user_id))
        print("Значение обновлено")

    else:
        print("Пользователь не найден в базе")


def get_user_data(user_id: int):  # функция для выбора значений в таблице
    if is_user_in_db(user_id):
        sql_query = (
            f"SELECT * " f"FROM {DB_TABLE_USERS_NAME} " f"WHERE user_id = {user_id}"
        )

        row = execute_query(sql_query)[0]
        result = {"subject": row[2], "level": row[3], "task": row[4], "answer": row[5]}
        return result


def delete_user(user_id: int):  # функция удаления пользователя
    if is_user_in_db(user_id):
        sql_query = f"DELETE " f"FROM {DB_TABLE_USERS_NAME} " f"WHERE user_id = ?;"

        execute_query(sql_query, (user_id,))
        print("Пользователь удалён")

    else:
        print("Пользователь не найден в базе")
