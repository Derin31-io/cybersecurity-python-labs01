import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.student import STUDENT_NAME, VARIANT_NUMBER

users = {
    "ciso_office": {"role": "ciso", "clearance": 4, "department": "Executive", "active": True},
    "threat_hunter": {"role": "threat_analyst", "clearance": 3, "department": "Threat Intel", "active": True},
    "junior_dev": {"role": "junior_developer", "clearance": 2, "department": "Development", "active": True},
    "visitor_acc": {"role": "visitor", "clearance": 1, "department": "Guest", "active": True},
    "legacy_sys": {"role": "legacy", "clearance": 2, "department": "Legacy", "active": False}
}


resources = [("threat_intelligence", 4), ("malware_samples", 3),
("coding_guidelines", 2), ("visitor_wifi", 1), ("strategic_plans", 4),
("demo_environment", 1), ("risk_assessments", 3), ("crypto_keys", 4),
("api_documentation", 2), ("guest_portal", 1)]

security_levels = ("Guest", "Employee", "Privileged", "Executive")
blocked_users = {"legacy_sys", "malicious_user", "expired_guest"}


def check_access():
    """Система розмежування доступу користувачів до ресурсів."""
    print(f"--- Контроль доступу | {STUDENT_NAME} (Варіант {VARIANT_NUMBER}) ---\n")

    # 1. Виведення списку всіх ресурсів із текстовими назвами рівнів
    print("Список ресурсів системи:")
    for res_name, res_level in resources:
        # Оскільки рівні від 1 до 4, віднімаємо 1 для правильного індексу кортежу (0-3)
        level_name = security_levels[res_level - 1]
        print(f"- {res_name}: {level_name}")

    print("\n" + "-" * 60)
    print("Результати перевірки доступу:")
    print("-" * 60)

    # Створюємо список користувачів для перевірки
    # Додаємо 'unknown_user', щоб спрацювало правило 'User not found'
    users_to_test = list(users.keys()) + ["unknown_user"]

    # 2. Алгоритм перевірки для кожного користувача та кожного ресурсу
    for username in users_to_test:
        for res_name, res_level in resources:

            # Перевірка згідно з пріоритетністю правил
            if username not in users:
                result = "DENY (User not found)"
            elif username in blocked_users:
                result = "DENY (User is blocked)"
            elif users[username].get("active") is False:
                result = "DENY (Account inactive)"
            else:
                user_clearance = users[username].get("clearance", 0)
                if user_clearance >= res_level:
                    result = "ALLOW"
                else:
                    result = "DENY (Insufficient clearance)"

            # Форматований вивід результату
            print(f"user={username:<15} resource={res_name:<20} -> {result}")

    print("-" * 60)


if __name__ == "__main__":
    check_access()