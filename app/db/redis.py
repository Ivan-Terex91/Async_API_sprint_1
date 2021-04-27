from aioredis import Redis

from core import json

redis: Redis = None

# Функция понадобится при внедрении зависимостей
async def get_redis() -> Redis:
    return redis


CACHE_EXPIRE_IN_SECONDS = 60


class RedisStorage:
    """Хранилище redis для кэша"""

    def __init__(self, redis):
        self.redis = redis

    async def get_data_in_redis(self, key):
        return await self.redis.get(key=key)

    async def put_data_from_redis(self, key, value):
        await self.redis.set(key=key, value=json.dumps(value), expire=CACHE_EXPIRE_IN_SECONDS)
