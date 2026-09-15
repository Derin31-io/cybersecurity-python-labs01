import os
import random
import string
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.student import STUDENT_NAME, VARIANT_NUMBER

passwords = ["Security@2023", "pass", "MyStr0ng#Key", "root", "Advanc3d@Pass", "user", "Protec7!Pass", "1234", "Elite@Secur1ty", "admin123"]

criteria = {
    "min_length": 7,
    "require_digits": True,
    "require_upper": True,
    "require_special": True
}

forbidden_passwords = {"pass", "root", "user", "1234", "admin123", "password"}


def analyze_passwords():
    """Функція для аналізу надійності паролів."""
    print(f"--- Аналіз паролів | {STUDENT_NAME} (Варіант {VARIANT_NUMBER}) ---")

    # 1. Генерація 3 випадкових індексів та додавання дублікатів
    random_indices = random.sample(range(len(passwords)), 3)
    for idx in random_indices:
        passwords.append(passwords[idx])

    print(f"Загальна кількість паролів після імітації дублювання: {len(passwords)}\n")

    # Заголовок таблиці
    print("-" * 75)
    print(f"| {'Пароль':<20} | {'Статус':<15} | {'Довж.':<5} | {'Унікальний':<10} |")
    print("-" * 75)

    min_len = criteria["min_length"]

    # 2. Оцінка надійності кожного пароля
    for pwd in passwords:
        # Перевірка наявності різних типів символів
        has_lower = any(c.islower() for c in pwd)
        has_upper = any(c.isupper() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_special = any(c in string.punctuation for c in pwd)

        # Підрахунок загальної кількості виконаних критеріїв (з 4 можливих)
        criteria_met_count = sum([has_lower, has_upper, has_digit, has_special])

        # Перевірка обов'язкових критеріїв для Варіанту 4
        all_required_met = (has_upper and has_digit and has_special)

        # Перевірка на унікальність у всьому списку
        is_unique = passwords.count(pwd) == 1

        # Логіка визначення статусу за алгоритмом з методички
        if pwd in forbidden_passwords or len(pwd) < min_len:
            status = "Заборонений"
        elif all_required_met and len(pwd) >= min_len + 4 and is_unique:
            status = "Дуже сильний"
        elif all_required_met:
            status = "Сильний"
        elif criteria_met_count >= 2:
            status = "Середній"
        else:
            status = "Слабкий"

        unique_text = "Так" if is_unique else "Ні"

        # Вивід рядка таблиці
        print(f"| {pwd:<20} | {status:<15} | {len(pwd):<5} | {unique_text:<10} |")

    print("-" * 75)


if __name__ == "__main__":
    analyze_passwords()