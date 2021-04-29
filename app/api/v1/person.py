from enum import Enum
from http import HTTPStatus
from typing import List, Optional
from uuid import UUID

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


@router.get("/{person_id:uuid}/", response_model=Person)
async def person_details(
    person_id: UUID, person_service: PersonService = Depends(get_person_service)
) -> Person:
    person, person_roles, film_ids = await person_service.get_by_id(person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="person not found")
    return Person(id=person.id, full_name=person.full_name, roles=person_roles, film_ids=film_ids)


@router.get("/{person_id:uuid}/film/", response_model=List[PersonFilm])
async def person_film_list(
    person_id: UUID, person_service: PersonService = Depends(get_person_service)
) -> List[PersonFilm]:
    films = await person_service.get_person_film_list(person_id)
    return [PersonFilm(**film) for film in films]


@router.get("/search/", response_model=List[Person])
async def person_search(
    page: Optional[int] = 1,
    size: Optional[int] = 50,
    query: Optional[str] = "",
    person_service: PersonService = Depends(get_person_service),
) -> List[Person]:
    persons_full_data = await person_service.search_person_by_full_name(
        page=page, size=size, match_obj=query
    )
    persons = []
    for person_full_data in persons_full_data:
        person, person_roles, film_ids = person_full_data
        persons.append(
            Person(id=person.id, full_name=person.full_name, roles=person_roles, film_ids=film_ids)
        )
    return persons
