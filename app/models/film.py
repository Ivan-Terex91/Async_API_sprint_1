from typing import List, Optional

from pydantic import UUID4

from core.models import BaseModel


class Person(BaseModel):
    id: UUID4
    full_name: str


class Genre(BaseModel):
    id: UUID4
    name: str


class Film(BaseModel):
    id: UUID4
    title: str
    imdb_rating: Optional[float]
    description: str
    genres: List[Genre]
    actors: List[Person]
    writers: List[Person]
    directors: List[Person]
