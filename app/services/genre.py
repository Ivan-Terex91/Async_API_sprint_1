from functools import lru_cache
from typing import List, Optional

from aioredis import Redis
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre

GENRE_CACHE_EXPIRE_IN_SECONDS = 60 * 5


class GenreService:
    """Бизнесс логика получения жанров"""

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, genre_id: str) -> Optional[Genre]:
        """Метод получения данных о жанре"""
        genre = await self._get_genre_from_elastic(genre_id)
        if not genre:
            return None
        return genre

    async def get_genres_list(
        self, page: int, size: int, sort_value: str, sort_order: str
    ) -> List[Genre]:
        """Метод получения данных о списке жанров из elastic"""
        docs = await self.elastic.search(
            index="genres", sort=f"{sort_value}:{sort_order}", from_=(page - 1) * size, size=size
        )
        return [Genre(**doc["_source"]) for doc in docs["hits"]["hits"]]

    async def _get_genre_from_elastic(self, genre_id: str) -> Optional[Genre]:
        """Метод получения данных о жанре из elastic."""
        try:
            doc = await self.elastic.get("genres", id=genre_id)
        except NotFoundError:
            return None
        return Genre(**doc["_source"])


@lru_cache()
def get_genre_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(redis, elastic)
