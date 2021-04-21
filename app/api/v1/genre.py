from http import HTTPStatus
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4, BaseModel

from services.genre import GenreService, get_genre_service

router = APIRouter()


class Genre(BaseModel):
    """Модель ответа для жанров"""

    id: UUID4
    name: str


@router.get("/{genre_id}", response_model=Genre)
async def genre_details(
    genre_id: str, genre_service: GenreService = Depends(get_genre_service)
) -> Genre:
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="genre not found")
    return Genre(id=genre.id, name=genre.name)


@router.get("/", response_model=List[Genre])
async def genre_list(
    page: Optional[int] = 1,
    size: Optional[int] = 5,
    genre_service: GenreService = Depends(get_genre_service),
) -> List[Genre]:
    genres = await genre_service.get_genres_list(page, size)
    return [Genre(id=genre.id, name=genre.name) for genre in genres]
