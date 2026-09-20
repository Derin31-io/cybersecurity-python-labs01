import csv
import datetime
import functools
import hashlib
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER


class ValidationError(Exception):
    pass


HASH_ALGORITHM = "sha512"
MIN_PASSWORD_LENGTH = 14

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_CSV_PATH = os.path.join(DATA_DIR, "users.csv")
LOG_JSON_PATH = os.path.join(DATA_DIR, "log.json")

SALT = str(VARIANT_NUMBER).zfill(5)


def log_event(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        username = kwargs.get("username") or (args[0] if args else "unknown")

        result_bool = func(*args, **kwargs)
        result_str = "success" if result_bool else "failure"

        log_entry = {
            "event": "login",
            "user": username,
            "result": result_str,
            "timestamp": datetime.datetime.now(
                datetime.timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "args": list(args),
            "kwargs": kwargs,
        }

        try:
            os.makedirs(DATA_DIR, exist_ok=True)

            logs = []

            if os.path.exists(LOG_JSON_PATH):
                try:
                    with open(LOG_JSON_PATH, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                except (json.JSONDecodeError, OSError):
                    logs = []

            logs.append(log_entry)

            with open(LOG_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=4, ensure_ascii=False)

        except (OSError, PermissionError) as e:
            print(f"Помилка запису логів: {e}")

        return result_bool

    return wrapper


def generate_hash(password: str, salt: str = "00000") -> str:
    if not password or not salt:
        raise ValueError("Пароль та сіль не можуть бути порожніми.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Пароль коротший за мінімальну довжину "
            f"({MIN_PASSWORD_LENGTH} символів)."
        )

    data_to_hash = (password + salt).encode("utf-8")

    hash_obj = hashlib.new(HASH_ALGORITHM, data_to_hash)

    return hash_obj.hexdigest()


def create_user(username: str, password: str) -> tuple:
    hash_val = generate_hash(password, SALT)
    return username, hash_val


def create_users(users_list: list):
    records = []

    for uname, pwd in users_list:
        try:
            records.append(create_user(uname, pwd))

        except (ValueError, ValidationError) as e:
            print(f"Помилка створення користувача {uname}: {e}")

    try:
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(
            USERS_CSV_PATH,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:
            writer = csv.writer(f)

            writer.writerow(["username", "password_hash"])
            writer.writerows(records)

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Системна помилка при збереженні користувачів: {e}")


def load_users_db() -> list:
    users_db = []

    if not os.path.exists(USERS_CSV_PATH):
        return users_db

    try:
        with open(USERS_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)

            next(reader, None)

            for row in reader:
                if row:
                    users_db.append(row)

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Системна помилка при зчитуванні бази даних: {e}")

    return users_db


@log_event
def login(username: str, password: str) -> bool:
    try:
        if not username or not password:
            raise ValueError("Логін та пароль є обов'язковими.")

        users_db = load_users_db()

        current_hash = generate_hash(password, SALT)

        for db_user, db_hash in users_db:
            if db_user == username and db_hash == current_hash:
                return True

    except (ValueError, ValidationError) as e:
        print(f"Помилка входу для {username}: {e}")

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Системна помилка при спробі входу: {e}")

    return False


def main():
    print(
        f"Студент: {STUDENT_NAME} | "
        f"Група: {GROUP_NAME} | "
        f"Варіант: {VARIANT_NUMBER}\n"
    )

    users_to_register = [
        ("admin", "SuperSecurePassword!2024"),
        ("moderator", "Moderator#PassPhrase99"),
        ("user1", "MyLongPassword@12345"),
        ("user2", "Another14Char+Passwd"),
        ("user3", "CyberSec!Student2023"),
        ("alice", "AliceInWonderland$!"),
        ("bob", "BobBuilder%Secure12"),
        ("charlie", "CharlieChaplin#1234"),
        ("dave", "DaveIsSafe&Sound77"),
        ("eve", "EveEavesdropper*99")
    ]

    print("Реєстрація користувачів")
    create_users(users_to_register)

    print("\nЧитання CSV бази")
    db_data = load_users_db()

    print(f"{'Логін':<15} | {'Хеш пароля':<30}")
    print("-" * 50)

    for u, h in db_data:
        print(f"{u:<15} | {h[:27]}...")

    print("\nСпроби входу")

    print(
        "Вхід admin (вірно):",
        login("admin", "SuperSecurePassword!2024")
    )

    print(
        "Вхід admin (невірно):",
        login("admin", "Wrong123!")
    )


if __name__ == "__main__":
    main()