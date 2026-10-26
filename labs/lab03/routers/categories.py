"""Маршрути FastAPI для керування категоріями."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status

from labs.lab03 import repository
from labs.lab03.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["Категорії"])


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Отримати список категорій",
)
def get_categories() -> list[dict[str, object]]:
    """Повернути всі категорії за зростанням їхнього ідентифікатора."""
    try:
        return repository.list_categories()
    except repository.DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити нову категорію",
    responses={
        status.HTTP_409_CONFLICT: {"description": "Назва категорії вже існує"},
    },
)
def create_category(payload: CategoryCreate) -> dict[str, object]:
    """Додати нову категорію спостережень."""
    try:
        return repository.create_category(payload.name)
    except repository.ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except repository.DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити порожню категорію",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Категорію не знайдено"},
        status.HTTP_409_CONFLICT: {"description": "Категорія містить записи"},
    },
)
def delete_category(
    category_id: Annotated[
        int,
        Path(gt=0, description="Додатний ідентифікатор категорії"),
    ],
) -> Response:
    """Видалити категорію, якщо до неї не прив'язано жодного запису."""
    try:
        repository.delete_category(category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except repository.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except repository.ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except repository.DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
