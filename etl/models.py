from dataclasses import asdict, dataclass, field
from typing import List, Optional

FilmworkIDType = str
PersonIDType = str
GenreIDType = str


@dataclass
class FilmworkPerson:
    id: str
    full_name: str
    role: Optional[str] = field(default=None)

    def to_dict(self):
        return asdict(self)


@dataclass
class Person:
    id: str
    full_name: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Genre:
    id: str
    name: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Filmwork:
    id: str
    filmwork_type: str
    title: str
    description: str
    imdb_rating: Optional[float] = field(default=None)
    genres: List[Genre] = field(default_factory=list)
    directors: List[Person] = field(default_factory=list)
    writers: List[Person] = field(default_factory=list)
    actors: List[Person] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
