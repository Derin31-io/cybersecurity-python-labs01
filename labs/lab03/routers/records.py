"""Маршрути FastAPI для керування записами та пакетного додавання."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query, Response, status

from labs.lab03 import repository
from labs.lab03.schemas import RecordCreate, RecordRead, RecordReplace, StatusType

router = APIRouter(prefix="/records", tags=["Записи"])


@router.get(
    "",
    response_model=list[RecordRead],
    summary="Отримати список записів із фільтрами",
)
def get_records(
    category_id: Annotated[
        int | None,
        Query(gt=0, description="Фільтр за ідентифікатором категорії"),
    ] = None,
    record_status: Annotated[
        StatusType | None,
        Query(alias="status", description="Фільтр за статусом опрацювання"),
    ] = None,
    min_value: Annotated[
        int | None,
        Query(ge=0, description="Мінімальна кількість подій (value >= min_value)"),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Буквальний підрядок у полі title (з урахуванням регістру)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Максимальна кількість записів на сторінці"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Кількість пропущених записів"),
    ] = 0,
) -> list[dict[str, object]]:
    """Повернути відфільтрований і відсортований за id список записів."""
    try:
        return repository.list_records(
            category_id=category_id,
            status=record_status,
            min_value=min_value,
            q=q,
            limit=limit,
            offset=offset,
        )
    except repository.DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/bulk",
    response_model=list[RecordRead],
    status_code=status.HTTP_201_CREATED,
    summary="Пакетне створення записів в одній транзакції",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Категорію одного з елементів не знайдено"
        },
        status.HTTP_409_CONFLICT: {
            "description": "Дублікат коду в базі або всередині пакета"
        },
    },
)
def create_records_bulk(
    payload: Annotated[
        list[RecordCreate],
        Body(
            min_length=1,
            max_length=100,
            description="Масив нових записів (від 1 до 100 елементів)",
        ),
    ],
) -> list[dict[str, object]]:
    """Атомарно зберегти пакет записів або скасувати весь пакет у разі помилки."""
    try:
        items = [item.model_dump() for item in payload]
        return repository.bulk_create_records(items)
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


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    summary="Отримати один запис за id",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Запис не знайдено"},
    },
)
def get_record(
    record_id: Annotated[
        int,
        Path(gt=0, description="Додатний ідентифікатор запису"),
    ],
) -> dict[str, object]:
    """Повернути детальну інформацію про один запис разом із назвою категорії."""
    try:
        return repository.get_record_by_id(record_id)
    except repository.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except repository.DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=RecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити новий запис",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Категорію не знайдено"},
        status.HTTP_409_CONFLICT: {"description": "Запис із таким code уже існує"},
    },
)
def create_record(payload: RecordCreate) -> dict[str, object]:
    """Створити новий запис спостереження за автентифікацією."""
    try:
        return repository.create_record(payload.model_dump())
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


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    summary="Повністю замінити змінювані поля запису",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Запис або категорію не знайдено"},
        status.HTTP_409_CONFLICT: {"description": "Дублікат поля code"},
    },
)
def replace_record(
    record_id: Annotated[
        int,
        Path(gt=0, description="Додатний ідентифікатор запису"),
    ],
    payload: RecordReplace,
) -> dict[str, object]:
    """Оновити всі змінювані поля наявного запису без зміни його id."""
    try:
        return repository.replace_record(record_id, payload.model_dump())
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


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити запис",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Запис не знайдено"},
    },
)
def delete_record(
    record_id: Annotated[
        int,
        Path(gt=0, description="Додатний ідентифікатор запису"),
    ],
) -> Response:
    """Видалити запис за його ідентифікатором."""
    try:
        repository.delete_record(record_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except repository.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except repository.DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
