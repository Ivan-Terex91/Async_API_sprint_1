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
        """Метод получения данных о жанре. Сначала из redis, затем из elastic."""
        genre = await self._genre_from_cache(genre_id)
        if not genre:
            genre = await self._get_genre_from_elastic(genre_id)
            if not genre:
                return None
            await self._put_genre_to_cache(genre)
        return genre

    async def get_genres_list(self, page: int, size: int = 5) -> List[Genre]:
        """Метод получения данных о списке жанров. Сначала из redis, затем из elastic"""
        genres = await self._genre_from_cache("genres")
        if not genres:
            genres = await self._get_genres_list_from_elastic(page, size)
            if not genres:
                return []
            for genre in genres:
                await self._put_genre_to_cache(genre)
        return genres

    async def _get_genre_from_elastic(self, genre_id: str) -> Optional[Genre]:
        """Метод получения данных о жанре из elastic."""
        try:
            doc = await self.elastic.get("genres", id=genre_id)
        except NotFoundError:
            return None
        return Genre(**doc["_source"])

    async def _get_genres_list_from_elastic(
        self, page: int, size: int = 5
    ) -> Optional[List[Genre]]:
        """Метод получения данных о списке жанров из elastic с сортировкой по названию жанра и пагинацией."""
        docs = await self.elastic.search(
            index="genres", sort="name", from_=(page - 1) * size, size=size
        )
        genres = [Genre(**doc["_source"]) for doc in docs["hits"]["hits"]]
        return genres

    async def _genre_from_cache(self, genre_id: str) -> Optional[Genre]:
        """Метод получения данных о жанре в redis."""
        data = await self.redis.get(genre_id)
        if not data:
            return None
        genre = Genre.parse_raw(data)
        return genre

    async def _put_genre_to_cache(self, genre: Genre):
        """Метод сохранения данных о жанре в redis."""
        await self.redis.set(genre.id, genre.json(), expire=GENRE_CACHE_EXPIRE_IN_SECONDS)


@lru_cache()
def get_genre_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(redis, elastic)
