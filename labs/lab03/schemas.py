"""Pydantic-моделі запитів і відповідей для варіантів 4-6 (лічильники подій)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StatusType = Literal["new", "in_progress", "done"]


class CategoryCreate(BaseModel):
    """Модель для створення нової категорії."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    name: str = Field(
        min_length=2,
        max_length=40,
        description="Унікальна назва категорії (2-40 символів)",
    )


class CategoryRead(CategoryCreate):
    """Модель для читання категорії."""

    id: int = Field(gt=0, description="Ідентифікатор категорії")


class SeedCategory(CategoryRead):
    """Модель категорії для початкового заповнення з фіксованим id."""


class RecordCreate(BaseModel):
    """Модель для створення запису про події автентифікації."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    code: str = Field(
        min_length=3,
        max_length=40,
        description="Унікальний код запису, наприклад V04-01",
    )
    title: str = Field(
        min_length=3,
        max_length=120,
        description="Назва або опис інтервалу спостереження",
    )
    category_id: int = Field(
        gt=0,
        strict=True,
        description="Ідентифікатор наявної категорії",
    )
    value: int = Field(
        ge=0,
        strict=True,
        description="Кількість подій у спостереженні (ціле число >= 0)",
    )
    status: StatusType = Field(
        description="Стан перевірки спостереження (new, in_progress, done)",
    )


class RecordReplace(RecordCreate):
    """Модель для повної заміни змінюваних полів запису (PUT)."""


class RecordRead(RecordCreate):
    """Модель для повернення запису клієнту разом із назвою категорії."""

    id: int = Field(gt=0, description="Ідентифікатор запису")
    category_name: str = Field(description="Назва категорії")


class SeedData(BaseModel):
    """Модель для перевірки структури файлу seed.json."""

    model_config = ConfigDict(extra="forbid")

    categories: list[SeedCategory] = Field(min_length=3, max_length=3)
    records: list[RecordCreate] = Field(min_length=8, max_length=8)
