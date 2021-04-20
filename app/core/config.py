import os
from logging import config as logging_config

from core.logger import LOGGING

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)

# Название проекта. Используется в Swagger-документации
PROJECT_NAME = os.getenv("PROJECT_NAME", "movies")

# Настройки Redis
REDIS_DSN = os.getenv("REDIS_DSN", "redis://localhost:6379/0")

# Настройки Elasticsearch
ELASTIC_DSN = os.getenv("ELASTIC_DSN", "http://localhost:9200/")

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
