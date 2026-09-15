import hashlib
import csv
import json
import os
import sys
import datetime
from functools import wraps

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from shared.student import STUDENT_NAME, VARIANT_NUMBER


PERSONAL_SALT = str(VARIANT_NUMBER).zfill(5)
MIN_PASS_LENGTH = 14


# 1. Створення власного винятку
class ValidationError(Exception):
    """Виняток для помилок валідації пароля."""
    pass


# 2. Функція хешування
def generate_hash(password: str, salt: str = "00000") -> str:
    if not password or not salt:
        raise ValueError("Пароль або сіль не можуть бути порожніми.")
    if len(password) < MIN_PASS_LENGTH:
        raise ValidationError(f"Пароль надто короткий. Мінімальна довжина: {MIN_PASS_LENGTH}.")

    # Використовуємо sha512 для 4 варіанту
    hashed = hashlib.sha512((password + salt).encode('utf-8')).hexdigest()
    return hashed


# 3. Реєстрація користувачів
users_to_register = (
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
)


def create_user(username, password):
    hash_value = generate_hash(password, PERSONAL_SALT)
    return (username, hash_value)


def create_users(users_list):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, 'users.csv')

    with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for user in users_list:
            writer.writerow(create_user(user[0], user[1]))


# 4. Декоратор логування
def log_event(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result_status = "failure"
        username = args[0] if args else kwargs.get("username", "unknown")
        try:
            result = func(*args, **kwargs)
            if result:
                result_status = "success"
            return result
        except Exception:
            result_status = "failure"
            raise
        finally:
            log_entry = {
                "event": "login",
                "user": username,
                "result": result_status,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "args": list(args),
                "kwargs": kwargs
            }
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(data_dir, exist_ok=True)
            log_path = os.path.join(data_dir, 'log.json')

            logs = []
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        pass
            logs.append(log_entry)
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=4)

    return wrapper


# 5. Автентифікація та читання бази
@log_event
def login(username: str, password: str) -> bool:
    if not username or not password:
        raise ValueError("Логін або пароль порожні.")

    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'users.csv')

    # Виклик generate_hash може згенерувати ValidationError, якщо пароль < 14
    hash_attempt = generate_hash(password, PERSONAL_SALT)

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) == 2:
                db_user, db_hash = row
                if db_user == username and db_hash == hash_attempt:
                    return True
    return False


# 6. Головна функція з обробкою винятків
def main():
    print(f"--- Безпечна реєстрація | {STUDENT_NAME} (Варіант {VARIANT_NUMBER}) ---")
    try:
        # Створюємо базу
        print("Створення бази користувачів...")
        create_users(users_to_register)

        # Читаємо та виводимо базу
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'users.csv')
        print("\nБаза даних користувачів (users.csv):")
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    print(f"User: {row[0]:<10} | Hash: {row[1][:40]}...")

        # Тестуємо успішний логін
        print("\nСпроба входу для 'admin'...")
        if login("admin", "SuperSecurePassword!2024"):
            print("Успішний вхід!")

        # Тестуємо помилку валідації (короткий пароль)
        print("\nСпроба входу з коротким паролем...")
        login("user1", "short")

    except FileNotFoundError as e:
        print(f"Помилка файлу: {e}")
    except PermissionError as e:
        print(f"Помилка доступу: {e}")
    except IOError as e:
        print(f"Помилка вводу/виводу: {e}")
    except ValidationError as e:
        print(f"Помилка валідації: {e}")
    except ValueError as e:
        print(f"Некоректні дані: {e}")


if __name__ == "__main__":
    main()