from enum import Enum
from typing import List

from pydantic import UUID4

from core.models import BaseModel


class RoleType(Enum):
    """Роли в фильме."""

    actor = "actor"
    director = "director"
    writer = "writer"


class Person(BaseModel):
    """Персоны."""

    id: UUID4
    full_name: str


class PersonFilm(BaseModel):
    """Фильмы в которых учавствовала персона."""

    id: UUID4
    title: str
    imdb_rating: float
    roles: List[RoleType]
