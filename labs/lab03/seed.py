"""Скрипт початкового заповнення бази даних із файлу data/seed.json."""

import json
import sqlite3
import sys
from contextlib import closing

from pydantic import ValidationError

from labs.lab03.database import BASE_DIR, get_connection, initialize_database
from labs.lab03.schemas import SeedData

SEED_PATH = BASE_DIR / "data" / "seed.json"


def seed_database() -> None:
    """Перевірити seed.json та заповнити порожню базу даних в одній транзакції."""
    if not SEED_PATH.exists():
        print(f"Помилка: файл початкових даних не знайдено ({SEED_PATH}).")
        sys.exit(1)

    try:
        raw_content = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        seed_data = SeedData.model_validate(raw_content)
    except json.JSONDecodeError as exc:
        print(f"Помилка синтаксису JSON у файлі {SEED_PATH.name}: {exc}")
        sys.exit(1)
    except ValidationError as exc:
        print(f"Помилка перевірки початкових даних у {SEED_PATH.name}:\n{exc}")
        sys.exit(1)

    initialize_database()

    try:
        with closing(get_connection()) as connection:
            cat_count = connection.execute(
                "SELECT COUNT(*) FROM categories"
            ).fetchone()[0]
            rec_count = connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]

            if cat_count > 0 or rec_count > 0:
                print(
                    f"База даних уже містить дані (категорій: {cat_count}, "
                    f"записів: {rec_count}). Повторне заповнення пропущено."
                )
                return

            with connection:
                connection.executemany(
                    "INSERT INTO categories (id, name) VALUES (?, ?)",
                    [(cat.id, cat.name) for cat in seed_data.categories],
                )
                connection.executemany(
                    """
                    INSERT INTO records (code, title, category_id, value, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            rec.code,
                            rec.title,
                            rec.category_id,
                            rec.value,
                            rec.status,
                        )
                        for rec in seed_data.records
                    ],
                )
            print(
                f"Базу даних успішно заповнено: додано {len(seed_data.categories)} "
                f"категорії та {len(seed_data.records)} записів."
            )
    except sqlite3.IntegrityError as exc:
        print(
            "Помилка цілісності даних під час заповнення бази "
            f"(транзакцію скасовано): {exc}"
        )
        sys.exit(1)
    except sqlite3.Error as exc:
        print(f"Технічна помилка SQLite під час заповнення бази: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
