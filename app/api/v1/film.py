from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.film import FilmService, get_film_service

router = APIRouter()


class Film(BaseModel):
    id: str
    title: str


# Внедряем FilmService с помощью Depends(get_film_service)
# TODO (smdnv): Заменить на использование реального сервиса FilmService
# @router.get("/{film_id}", response_model=Film)
# async def film_details(
#     film_id: str, film_service: FilmService = Depends(get_film_service)
# ) -> Film:
@router.get("/{film_id}", response_model=Film)
async def film_details(film_id: str) -> Film:
    # film = await film_service.get_by_id(film_id)
    film = Film(id="1d2ecbbd-4ab2-4b0b-991d-0827b6e5e8d1", title="Hello World")
    if not film:
        # Если фильм не найден, отдаём 404 статус
        # Желательно пользоваться уже определёнными HTTP-статусами, которые содержат enum
        # Такой код будет более поддерживаемым
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")

    # Перекладываем данные из models.Film в Film
    # Обратите внимание, что у модели бизнес-логики есть поле description
    # Которое отсутствует в модели ответа API.
    # Если бы использовалась общая модель для бизнес-логики и формирования ответов API
    # вы бы предоставляли клиентам данные, которые им не нужны
    # и, возможно, данные, которые опасно возвращать
    return Film(id=film.id, title=film.title)
