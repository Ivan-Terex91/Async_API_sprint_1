import logging

import aioredis
import uvicorn as uvicorn
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.v1 import film, genre
from core import config
from core.logger import LOGGING
from db import elastic, redis

app = FastAPI(
    title=config.PROJECT_NAME,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
)


@app.on_event("startup")
async def startup():
    """
    Подключаемся к базам при старте сервера
    Подключиться можем при работающем event-loop
    Поэтому логика подключения происходит в асинхронной функции
    """
    redis.redis = await aioredis.create_redis_pool(config.REDIS_DSN, minsize=10, maxsize=20)
    elastic.es = AsyncElasticsearch(hosts=[config.ELASTIC_DSN])


@app.on_event("shutdown")
async def shutdown():
    """
    Отключаемся от баз при выключении сервера
    """
    await redis.redis.close()
    await elastic.es.close()


# Подключаем роутер к серверу, указав префикс /v1/film
# Теги указываем для удобства навигации по документации
app.include_router(film.router, prefix="/api/v1/film", tags=["film"])
app.include_router(genre.router, prefix="/api/v1/genre", tags=["genre"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config=LOGGING,
        log_level=logging.DEBUG,
    )
