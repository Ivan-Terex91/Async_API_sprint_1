from functools import lru_cache
from typing import Dict, List, Optional

from aioredis import Redis
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from core import json
from db.elastic import get_elastic
from db.redis import get_redis
from models.person import Person, PersonFilm, RoleType

PERSON_CACHE_EXPIRE_IN_SECONDS = 60 * 5


class PersonService:
    """Бизнес логика получения персон."""

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, person_id: str) -> Optional[Person]:
        """Метод получения данных о персоне. Сначала из redis, затем из elastic."""
        person = await self._person_from_cache(person_id)
        if not person:
            person = await self._get_person_from_elastic(person_id)
            if not person:
                return None
            await self._put_person_to_cache(person)
        films = await self.get_person_film_data(person, source_param=["id"])
        film_ids = set()
        person_roles = []
        for role, film in films.items():
            person_roles.append(role)
            film_ids.update({film_param["id"] for film_param in film})
        return person, person_roles, list(film_ids)

    async def get_person_film_list(self, person_id: str) -> Optional[List[PersonFilm]]:
        """Метод получения списка фильмов в которых принимала участие персона."""
        person = await self._person_from_cache(person_id)
        if not person:
            person = await self._get_person_from_elastic(person_id)
            if not person:
                return []
            await self._put_person_to_cache(person)
        films = await self.get_person_film_data(person, source_param=["id", "title", "imdb_rating"])
        person_films = {}
        for role, film in films.items():
            for film_param in film:
                if film_param["id"] not in person_films:
                    film_param["roles"] = [role]
                    person_films[film_param["id"]] = film_param
                else:
                    person_films[film_param["id"]]["roles"].append(role)
        return [film_param for film_param in person_films.values()]

    async def _get_person_from_elastic(self, person_id: str) -> Optional[Person]:
        """Метод получения данных о персоне из elastic."""
        try:
            doc = await self.elastic.get("persons", id=person_id)
        except NotFoundError:
            return None
        return Person(**doc["_source"])

    async def get_person_film_data(self, person: Person, source_param: List) -> Dict:
        """Метод возвращает данные фильмов в которых учавствовала персона."""
        person_films_data = {}
        all_roles = [role.value for role in RoleType]
        for role in all_roles:
            path = f"{role}s"
            term = {f"{path}.id": person.id}
            query = self.get_query(_source_param=source_param, path=path, term=term)
            films = await self.elastic.search(index="movies", body=json.dumps(query))
            films = films["hits"]["hits"]
            if films:
                person_films_data[role] = [film["_source"] for film in films]
        return person_films_data

    async def _person_from_cache(self, person_id: str) -> Optional[Person]:
        """Метод получения данных о персоне в redis."""
        data = await self.redis.get(person_id)
        if not data:
            return None
        person = Person.parse_raw(data)
        return person

    async def _put_person_to_cache(self, person: Person):
        """Метод сохранения данных о персоне в redis."""
        await self.redis.set(person.id, person.json(), expire=PERSON_CACHE_EXPIRE_IN_SECONDS)

    @staticmethod
    async def get_query(_source_param: List, path: str, term: Dict) -> Dict:
        """Метод формирует запрос к elastic в зависимости от параметров."""
        query = {
            "_source": _source_param,
            "query": {"nested": {"path": path, "query": {"term": term}}},
        }
        return query


@lru_cache()
def get_person_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    return PersonService(redis, elastic)
