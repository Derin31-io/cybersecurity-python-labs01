"""Шар доступу до даних (SQL-операції та керування транзакціями)."""

import logging
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from typing import Any

from labs.lab03.database import get_connection

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Базовий виняток шару роботи з базою даних."""


class NotFoundError(RepositoryError):
    """Запис або потрібна категорія не існує."""


class ConflictError(RepositoryError):
    """Конфлікт унікальності або спроба видалити непорожню категорію."""


class DatabaseOperationError(RepositoryError):
    """Неочікувана технічна помилка бази даних."""


def _row_to_category(row: sqlite3.Row) -> dict[str, Any]:
    """Перетворити рядок SQLite на словник категорії."""
    return {"id": row["id"], "name": row["name"]}


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    """Перетворити рядок SQLite на словник запису."""
    return {
        "id": row["id"],
        "code": row["code"],
        "title": row["title"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "value": row["value"],
        "status": row["status"],
    }


def list_categories() -> list[dict[str, Any]]:
    """Отримати список усіх категорій за зростанням id."""
    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, name FROM categories ORDER BY id ASC"
            ).fetchall()
            return [_row_to_category(row) for row in rows]
    except sqlite3.Error as exc:
        logger.exception("Помилка під час отримання списку категорій")
        raise DatabaseOperationError("Помилка читання категорій із бази даних") from exc


def create_category(name: str) -> dict[str, Any]:
    """Створити нову категорію."""
    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)",
                    (name,),
                )
                category_id = cursor.lastrowid
                row = connection.execute(
                    "SELECT id, name FROM categories WHERE id = ?",
                    (category_id,),
                ).fetchone()
            if row is None:
                raise DatabaseOperationError("Не вдалося прочитати створену категорію")
            return _row_to_category(row)
    except sqlite3.IntegrityError as exc:
        logger.warning("Конфлікт під час створення категорії '%s': %s", name, exc)
        raise ConflictError(f"Категорія з назвою '{name}' уже існує") from exc
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час створення категорії")
        raise DatabaseOperationError("Помилка збереження категорії") from exc


def delete_category(category_id: int) -> None:
    """Видалити порожню категорію за id."""
    try:
        with closing(get_connection()) as connection, connection:
            exists = connection.execute(
                "SELECT 1 FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()
            if exists is None:
                raise NotFoundError(f"Категорію з id={category_id} не знайдено")

            connection.execute(
                "DELETE FROM categories WHERE id = ?",
                (category_id,),
            )
    except NotFoundError:
        raise
    except sqlite3.IntegrityError as exc:
        logger.warning(
            "Спроба видалити непорожню категорію id=%s: %s", category_id, exc
        )
        raise ConflictError(
            "Неможливо видалити категорію, оскільки вона містить пов'язані записи"
        ) from exc
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час видалення категорії")
        raise DatabaseOperationError("Помилка видалення категорії") from exc


def get_record_by_id(record_id: int) -> dict[str, Any]:
    """Отримати один запис за id разом із назвою категорії."""
    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT r.id, r.code, r.title, r.category_id,
                       c.name AS category_name, r.value, r.status
                FROM records r
                JOIN categories c ON r.category_id = c.id
                WHERE r.id = ?
                """,
                (record_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"Запис з id={record_id} не знайдено")
            return _row_to_record(row)
    except NotFoundError:
        raise
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час отримання запису id=%s", record_id)
        raise DatabaseOperationError("Помилка читання запису з бази даних") from exc


def list_records(
    category_id: int | None = None,
    status: str | None = None,
    min_value: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Отримати список записів із динамічною фільтрацією та пагінацією."""
    clauses: list[str] = []
    params: list[Any] = []

    if category_id is not None:
        clauses.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        clauses.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        clauses.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        clauses.append("instr(r.title, ?) > 0")
        params.append(q)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT r.id, r.code, r.title, r.category_id,
               c.name AS category_name, r.value, r.status
        FROM records r
        JOIN categories c ON r.category_id = c.id
        {where_sql}
        ORDER BY r.id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query, tuple(params)).fetchall()
            return [_row_to_record(row) for row in rows]
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час вибірки записів")
        raise DatabaseOperationError("Помилка вибірки записів із бази даних") from exc


def create_record(data: dict[str, Any]) -> dict[str, Any]:
    """Створити новий запис у базі даних."""
    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cat = connection.execute(
                    "SELECT 1 FROM categories WHERE id = ?",
                    (data["category_id"],),
                ).fetchone()
                if cat is None:
                    raise NotFoundError(
                        f"Категорію з id={data['category_id']} не знайдено"
                    )

                cursor = connection.execute(
                    """
                    INSERT INTO records (code, title, category_id, value, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        data["code"],
                        data["title"],
                        data["category_id"],
                        data["value"],
                        data["status"],
                    ),
                )
                record_id = cursor.lastrowid
                row = connection.execute(
                    """
                    SELECT r.id, r.code, r.title, r.category_id,
                           c.name AS category_name, r.value, r.status
                    FROM records r
                    JOIN categories c ON r.category_id = c.id
                    WHERE r.id = ?
                    """,
                    (record_id,),
                ).fetchone()
            if row is None:
                raise DatabaseOperationError("Не вдалося прочитати створений запис")
            return _row_to_record(row)
    except NotFoundError:
        raise
    except sqlite3.IntegrityError as exc:
        logger.warning("Конфлікт під час створення запису '%s': %s", data["code"], exc)
        raise ConflictError(f"Запис із кодом '{data['code']}' уже існує") from exc
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час створення запису")
        raise DatabaseOperationError("Помилка збереження запису") from exc


def replace_record(record_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Повністю оновити змінювані поля запису за його id."""
    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                existing = connection.execute(
                    "SELECT 1 FROM records WHERE id = ?",
                    (record_id,),
                ).fetchone()
                if existing is None:
                    raise NotFoundError(f"Запис з id={record_id} не знайдено")

                cat = connection.execute(
                    "SELECT 1 FROM categories WHERE id = ?",
                    (data["category_id"],),
                ).fetchone()
                if cat is None:
                    raise NotFoundError(
                        f"Категорію з id={data['category_id']} не знайдено"
                    )

                connection.execute(
                    """
                    UPDATE records
                    SET code = ?, title = ?, category_id = ?, value = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        data["code"],
                        data["title"],
                        data["category_id"],
                        data["value"],
                        data["status"],
                        record_id,
                    ),
                )
                row = connection.execute(
                    """
                    SELECT r.id, r.code, r.title, r.category_id,
                           c.name AS category_name, r.value, r.status
                    FROM records r
                    JOIN categories c ON r.category_id = c.id
                    WHERE r.id = ?
                    """,
                    (record_id,),
                ).fetchone()
            if row is None:
                raise DatabaseOperationError("Не вдалося прочитати оновлений запис")
            return _row_to_record(row)
    except NotFoundError:
        raise
    except sqlite3.IntegrityError as exc:
        logger.warning(
            "Конфлікт під час оновлення запису id=%s ('%s'): %s",
            record_id,
            data["code"],
            exc,
        )
        raise ConflictError(f"Запис із кодом '{data['code']}' уже існує") from exc
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час оновлення запису id=%s", record_id)
        raise DatabaseOperationError("Помилка оновлення запису") from exc


def delete_record(record_id: int) -> None:
    """Видалити запис за id."""
    try:
        with closing(get_connection()) as connection, connection:
            existing = connection.execute(
                "SELECT 1 FROM records WHERE id = ?",
                (record_id,),
            ).fetchone()
            if existing is None:
                raise NotFoundError(f"Запис з id={record_id} не знайдено")

            connection.execute(
                "DELETE FROM records WHERE id = ?",
                (record_id,),
            )
    except NotFoundError:
        raise
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час видалення запису id=%s", record_id)
        raise DatabaseOperationError("Помилка видалення запису") from exc


def bulk_create_records(items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Пакетно додати записи в межах однієї транзакції."""
    try:
        with closing(get_connection()) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                created_ids: list[int] = []
                for item in items:
                    cat = connection.execute(
                        "SELECT 1 FROM categories WHERE id = ?",
                        (item["category_id"],),
                    ).fetchone()
                    if cat is None:
                        raise NotFoundError(
                            f"Категорію з id={item['category_id']} не знайдено"
                        )

                    cursor = connection.execute(
                        """
                        INSERT INTO records (code, title, category_id, value, status)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            item["code"],
                            item["title"],
                            item["category_id"],
                            item["value"],
                            item["status"],
                        ),
                    )
                    if cursor.lastrowid is None:
                        raise DatabaseOperationError(
                            "Не вдалося отримати id створеного запису"
                        )
                    created_ids.append(cursor.lastrowid)

                placeholders = ", ".join("?" for _ in created_ids)
                rows = connection.execute(
                    f"""
                    SELECT r.id, r.code, r.title, r.category_id,
                           c.name AS category_name, r.value, r.status
                    FROM records r
                    JOIN categories c ON r.category_id = c.id
                    WHERE r.id IN ({placeholders})
                    ORDER BY r.id ASC
                    """,
                    tuple(created_ids),
                ).fetchall()
                return [_row_to_record(row) for row in rows]
    except NotFoundError:
        raise
    except sqlite3.IntegrityError as exc:
        logger.warning("Конфлікт унікальності під час пакетного додавання: %s", exc)
        raise ConflictError(
            "Пакет містить дублікат коду запису (в базі або всередині пакета)"
        ) from exc
    except sqlite3.Error as exc:
        logger.exception("Помилка бази даних під час пакетного додавання записів")
        raise DatabaseOperationError("Помилка пакетного збереження записів") from exc
