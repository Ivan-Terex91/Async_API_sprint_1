from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from aioredis import Redis
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from core import json
from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film


class FilmService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        film = await self._get_film_from_elastic(film_id)
        return film

    async def get_page(
        self, filter_map: dict, page_number: int, page_size: int, sort_value: str, sort_order: str
    ) -> List[Film]:
        return await self._get_films_page_from_elastic(
            filter_map=filter_map,
            page_number=page_number,
            page_size=page_size,
            sort_value=sort_value,
            sort_order=sort_order,
        )

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        try:
            doc = await self.elastic.get(index="movies", id=film_id)
        except NotFoundError:
            return None

        return Film(**doc["_source"])

    async def _get_films_page_from_elastic(
        self, filter_map: dict, page_number: int, page_size: int, sort_value: str, sort_order: str
    ) -> List[Film]:

        search_query = {}
        if "genre_id" in filter_map:
            search_query["query"] = {
                "nested": {
                    "path": "genres",
                    "query": {"term": {"genres.id": str(filter_map["genre_id"])}},
                }
            }

        response = await self.elastic.search(
            index="movies",
            size=page_size,
            from_=(page_number - 1) * page_size,
            sort=[f"{sort_value}:{sort_order}"],
            body=search_query,
        )
        return [Film(**doc["_source"]) for doc in response["hits"]["hits"]]

    async def search_films(self, page: int, size: int, match_obj: str) -> List[Dict]:
        """Метод поиска фильмов по названию"""
        query = await self.get_search_query(
            _source_param=("id", "title", "imdb_rating"), field="title", match_obj=match_obj
        )
        films = await self.elastic.search(
            index="movies", body=json.dumps(query), from_=(page - 1) * size, size=size
        )
        films = films["hits"]["hits"]
        return films

    @staticmethod
    async def get_search_query(field: str, match_obj: str, _source_param: Tuple = ()) -> Dict:
        """Метод формирует поисковой запрос к elastic в зависимости от параметров."""
        query = {"_source": _source_param, "query": {"match": {field: match_obj}}}
        return query


@lru_cache()
def get_film_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
