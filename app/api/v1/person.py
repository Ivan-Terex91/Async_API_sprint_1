from enum import Enum
from http import HTTPStatus
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4, BaseModel

from services.person import PersonService, get_person_service

router = APIRouter()


class RoleType(Enum):
    """Роли в фильме."""

    actor = "actor"
    director = "director"
    writer = "writer"


class Person(BaseModel):
    """Модель ответа для персон."""

    id: UUID4
    full_name: str
    roles: List[RoleType]
    film_ids: List[UUID4]


class PersonFilm(BaseModel):
    """Модель ответа для фильмов в которых учавствовала персона."""

    id: UUID4
    title: str
    imdb_rating: float
    roles: List[RoleType]


@router.get("/{person_id}", response_model=Person)
async def person_details(
    person_id: str, person_service: PersonService = Depends(get_person_service)
) -> Person:
    person, person_roles, film_ids = await person_service.get_by_id(person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="person not found")
    return Person(id=person.id, full_name=person.full_name, roles=person_roles, film_ids=film_ids)


@router.get("/{person_id}/film/", response_model=List[PersonFilm])
async def person_film_list(
    person_id: str, person_service: PersonService = Depends(get_person_service)
) -> List[PersonFilm]:
    films = await person_service.get_person_film_list(person_id)
    return [
        PersonFilm(id=film.id, title=film.title, imdb_rating=film.imdb_rating, roles=film.roles)
        for film in films
    ]
