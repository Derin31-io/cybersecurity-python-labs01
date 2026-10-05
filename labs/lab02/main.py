import argparse
import logging
from datetime import timedelta
from pathlib import Path

from labs.lab02.task1 import Admin, User, UserAccount
from labs.lab02.task2 import analyze

LOGGER = logging.getLogger(__name__)


def demo() -> None:
    """Демонстрація Завдання 1."""
    user = User(
        "alice",
        "alice@example.com",
        "user",
        password="SecurePassword123!",
    )

    print("\n=== User ===")
    print(user)
    print(
        "Correct password:",
        user.check_password("SecurePassword123!"),
    )
    print(
        "Wrong password:",
        user.check_password("wrong"),
    )

    print("\n=== Email ===")
    user.email = "alice_new@example.com"
    print("New email:", user.email)

    try:
        user.email = "wrong-email"
    except ValueError as exc:
        print("Validation error:", exc)

    print("\n=== Admin ===")

    admin = Admin(
        "admin",
        "admin@example.com",
        password="AdminPassword123!",
    )

    admin.grant_permission("read_logs")
    admin.grant_permission("manage_users")

    print(admin)
    print(
        "Has manage_users:",
        admin.has_permission("manage_users"),
    )

    print("\n=== Login ===")

    account = UserAccount(user)

    print(
        "Successful:",
        account.login(
            "alice",
            "SecurePassword123!",
            "192.168.1.100",
        ),
    )

    print(
        "Failed:",
        account.login(
            "alice",
            "wrong",
            "192.168.1.100",
        ),
    )

    print(
        "Authenticated:",
        account.is_authenticated(),
    )

    print("\n=== Timeout ===")

    if account.session is not None:
        account.session.last_activity -= timedelta(
            seconds=UserAccount.SESSION_TIMEOUT_SEC + 1
        )

    print(
        "After timeout:",
        account.is_authenticated(),
    )

    print("\n=== Login again ===")

    account.login(
        "alice",
        "SecurePassword123!",
        "192.168.1.101",
    )

    print(
        "Authenticated:",
        account.is_authenticated(),
    )

    print("\n=== Logout ===")

    account.logout()

    print(
        "After logout:",
        account.is_authenticated(),
    )

    print("\n=== Audit Log ===")
    account.audit_log.show_all()

    print("\nDEMO FINISHED")


def main() -> None:
    """Точка входу CLI."""
    parser = argparse.ArgumentParser(description="Laboratory work №2")

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "demo",
        help="Run OOP demonstration",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze SSH authentication log",
    )

    analyze_parser.add_argument(
        "--auth-log",
        type=Path,
        required=True,
        help="Path to auth.log",
    )

    analyze_parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="Number of failed attempts required to detect brute-force",
    )

    analyze_parser.add_argument(
        "--window-min",
        type=int,
        default=5,
        help="Time window in minutes",
    )

    analyze_parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("labs/lab02/data/blocklist_ips.json"),
        help="Path to JSON report",
    )

    args = parser.parse_args()

    if args.command == "demo":
        demo()
        return

    if args.threshold <= 0:
        parser.error("--threshold must be greater than 0")

    if args.window_min <= 0:
        parser.error("--window-min must be greater than 0")

    analyze(
        args.auth_log,
        args.threshold,
        args.window_min,
        args.output_json,
    )


if __name__ == "__main__":
    main()
