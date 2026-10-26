"""Головний модуль FastAPI-застосунку для лабораторної роботи №3."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from labs.lab03.config import APP_DESCRIPTION, APP_TITLE, VARIANT_NUMBER
from labs.lab03.database import initialize_database
from labs.lab03.routers import categories, records
from shared import student as student_module


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці бази даних під час запуску сервера."""
    initialize_database()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)


def _extract_student_info() -> dict[str, str | int]:
    """Отримати дані студента з модуля shared.student."""
    if hasattr(student_module, "get_student_info"):
        info = student_module.get_student_info()
        if isinstance(info, dict):
            return {
                "student_name": str(
                    info.get("student_name")
                    or info.get("name")
                    or info.get("full_name")
                ),
                "group_name": str(info.get("group_name") or info.get("group")),
                "variant_number": int(
                    info.get("variant_number") or info.get("variant") or VARIANT_NUMBER
                ),
            }

    student_name = (
        getattr(student_module, "STUDENT_NAME", None)
        or getattr(student_module, "student_name", None)
        or getattr(student_module, "FULL_NAME", None)
        or getattr(student_module, "full_name", None)
        or getattr(student_module, "NAME", None)
        or getattr(student_module, "name", "Ім'я Прізвище")
    )
    group_name = (
        getattr(student_module, "GROUP_NAME", None)
        or getattr(student_module, "group_name", None)
        or getattr(student_module, "GROUP", None)
        or getattr(student_module, "group", "Група")
    )
    variant_number = (
        getattr(student_module, "VARIANT_NUMBER", None)
        or getattr(student_module, "variant_number", None)
        or getattr(student_module, "VARIANT", None)
        or getattr(student_module, "variant", VARIANT_NUMBER)
    )
    return {
        "student_name": str(student_name),
        "group_name": str(group_name),
        "variant_number": int(variant_number),
    }


@app.get("/ping", tags=["Система"], summary="Перевірка доступності API")
def ping() -> dict[str, str]:
    """Повернути статус працездатності сервісу."""
    return {"status": "ok"}


@app.get("/student", tags=["Система"], summary="Інформація про студента")
def get_student() -> dict[str, str | int]:
    """Повернути ПІБ, групу та номер варіанта з модуля shared/student.py."""
    return _extract_student_info()


app.include_router(categories.router)
app.include_router(records.router)

# http://127.0.0.1:8000/docs
# uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
