import enum
from http import HTTPStatus
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4, BaseModel

from services.film import FilmService, get_film_service

router = APIRouter()


class FilmOrderingEnum(enum.Enum):
    imdb_rating__asc = "imdb_rating"
    imdb_rating__desc = "-imdb_rating"


class PersonModel(BaseModel):
    id: UUID4
    full_name: str


class GenreModel(BaseModel):
    id: UUID4
    name: str


class FilmDetailsModel(BaseModel):
    id: UUID4
    title: str
    imdb_rating: Optional[float]
    description: str
    genre: List[GenreModel]
    actors: List[PersonModel]
    writers: List[PersonModel]
    directors: List[PersonModel]


class FilmListModel(BaseModel):
    id: UUID4
    title: str
    imdb_rating: Optional[float]


@router.get("/{film_id}", response_model=FilmDetailsModel)
async def film_details(
    film_id: str, film_service: FilmService = Depends(get_film_service)
) -> FilmDetailsModel:
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")

    return FilmDetailsModel(
        id=film.id,
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description,
        genre=film.genres,
        actors=film.actors,
        writers=film.writers,
        directors=film.directors,
    )


@router.get("/", response_model=List[FilmListModel])
async def film_list(
    sort: FilmOrderingEnum = Query(default=FilmOrderingEnum.imdb_rating__desc),
    page_number: int = Query(default=1, ge=1, alias="page[number]"),
    page_size: int = Query(default=50, ge=1, alias="page[size]"),
    filter_genre_id: UUID = Query(None, alias="filter[genre]"),
    film_service: FilmService = Depends(get_film_service),
):
    sort_value, sort_order = sort.name.split("__")

    filter_map = {}
    if filter_genre_id:
        filter_map["genre_id"] = filter_genre_id

    films_list = await film_service.get_page(
        filter_map=filter_map,
        page_number=page_number,
        page_size=page_size,
        sort_value=sort_value,
        sort_order=sort_order,
    )
    return films_list


@router.get("/search/", response_model=List[FilmListModel])
async def film_search(
    page: Optional[int] = 1,
    size: Optional[int] = 50,
    query: Optional[str] = "",
    film_service: FilmService = Depends(get_film_service),
) -> List[FilmListModel]:
    films = await film_service.search_films(page=page, size=size, match_obj=query)
    return [FilmListModel(**film["_source"]) for film in films]
