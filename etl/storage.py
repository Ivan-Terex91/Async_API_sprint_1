import abc
import json
from datetime import datetime
from functools import partialmethod
from pathlib import Path
from typing import Any, List, Optional, Tuple

import psycopg2
import requests
from psycopg2 import sql
from queries import (
    select_filmworks_genres_query,
    select_filmworks_participants_query,
    select_filmworks_query,
    select_modified_filmworks,
    select_modified_filmworks_from_genres,
    select_modified_filmworks_from_persons,
    select_modified_genres,
    select_modified_persons,
)
from utils import backoff

from models import FilmworkIDType, GenreIDType, PersonIDType


def is_db_reader_connection_error(e: Exception):
    return isinstance(e, psycopg2.OperationalError) and "Connection refused" in str(e)


def is_writer_connection_error(e: Exception):
    return isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))


class PGReader:
    """
    Класс для чтения данных из postgres
    """

    def __init__(self, postgres_dsn: str):
        self.postgres_dsn = postgres_dsn

    @backoff(
        on_predicate=is_db_reader_connection_error,
        border_sleep_time=60,
    )
    def read(self, query):
        with psycopg2.connect(self.postgres_dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()

    def read_modified_filmworks_by_query(
        self, query: str, last_timestamp: datetime, offset: int, limit: int
    ) -> List[str]:
        """
        Получение id фильмов, обновленных после last_timestamp
        """
        result = self.read(
            sql.SQL(query).format(
                last_timestamp=sql.Literal(last_timestamp.isoformat()),
                offset=sql.Literal(offset),
                limit=sql.Literal(limit),
            )
        )
        return [t[0] for t in result]

    read_modified_filmworks_from_persons = partialmethod(
        read_modified_filmworks_by_query, select_modified_filmworks_from_persons
    )
    read_modified_filmworks_from_genres = partialmethod(
        read_modified_filmworks_by_query, select_modified_filmworks_from_genres
    )
    read_modified_filmworks = partialmethod(
        read_modified_filmworks_by_query, select_modified_filmworks
    )

    def read_filmworks(self, filmworks_ids: List[FilmworkIDType]):
        """
        Получение фильмов по списку id
        """
        query = sql.SQL(select_filmworks_query).format(
            filmworks_ids=sql.SQL(",").join(sql.Literal(fw_id) for fw_id in filmworks_ids)
        )
        return self.read(query)

    def read_filmworks_participants(self, filmworks_ids: List[FilmworkIDType]):
        """
        Получение участников фильмов по списку id фильмов
        """
        query = sql.SQL(select_filmworks_participants_query).format(
            filmworks_ids=sql.SQL(",").join(sql.Literal(fw_id) for fw_id in filmworks_ids)
        )
        return self.read(query)

    def read_filmworks_genres(self, filmworks_ids: List[FilmworkIDType]):
        """
        Получение жанров по списку id фильмов
        """
        query = sql.SQL(select_filmworks_genres_query).format(
            filmworks_ids=sql.SQL(",").join(sql.Literal(fw_id) for fw_id in filmworks_ids)
        )
        return self.read(query)

    def read_modified_persons(
        self, last_timestamp: datetime, offset: int, limit: int
    ) -> List[Tuple[PersonIDType, str, str]]:
        """
        Получения данных о персонах, обновленных после last_timestamp
        """
        return self.read(
            sql.SQL(select_modified_persons).format(
                last_timestamp=sql.Literal(last_timestamp.isoformat()),
                offset=sql.Literal(offset),
                limit=sql.Literal(limit),
            )
        )

    def read_modified_genres(
        self, last_timestamp: datetime, offset: int, limit: int
    ) -> List[Tuple[GenreIDType, str]]:
        """
        Получения данных о жанрах, обновленных после last_timestamp
        """
        return self.read(
            sql.SQL(select_modified_genres).format(
                last_timestamp=sql.Literal(last_timestamp.isoformat()),
                offset=sql.Literal(offset),
                limit=sql.Literal(limit),
            )
        )


class ElasticWriter:
    """
    Класс для записи данных в elastic
    """

    def __init__(self, elastic_url: str):
        self.elastic_url = elastic_url
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    @backoff(
        on_predicate=is_writer_connection_error,
        border_sleep_time=60,
    )
    def write(self, method, url, **kwargs) -> dict:
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def bulk_create(
        self, index_name: str, items: List[Tuple[str, Any]]
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Создание документов в индексе
        """
        data = []
        for item_id, item in items:
            data.append(json.dumps({"create": {"_index": index_name, "_id": item_id}}))
            data.append(json.dumps(item))

        response = self.write("PUT", f"{self.elastic_url}/_bulk", data="\n".join(data) + "\n")

        errors_map = {}
        for item_error in response["items"]:
            create_result = item_error.get("create")
            if not create_result:
                continue

            create_error = create_result.get("error")
            if not create_error:
                continue

            error_type, error_msg = create_error["type"], create_error["reason"]
            errors_map[create_result["_id"]] = f"{error_type}: {error_msg}"

        return [(item_id, errors_map.get(item_id)) for item_id, _ in items]

    def bulk_update(
        self, index_name: str, items: List[Tuple[str, Any]]
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Обновление документов в индексе
        """
        data = []
        for item_id, item in items:
            data.append(json.dumps({"update": {"_index": index_name, "_id": item_id}}))
            data.append(json.dumps({"doc": item}))

        response = self.write("PUT", f"{self.elastic_url}/_bulk", data="\n".join(data) + "\n")

        errors_map = {}
        for item_error in response["items"]:
            update_result = item_error.get("update")
            if not update_result:
                continue

            update_error = update_result.get("error")
            if not update_error:
                continue

            error_type, error_msg = update_error["type"], update_error["reason"]
            errors_map[update_result["_id"]] = f"{error_type}: {error_msg}"

        return [(item_id, errors_map.get(item_id)) for item_id, _ in items]

    def bulk_create_or_update(
        self, index_name: str, items: List[Tuple[str, Any]]
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Создание или обновление документов в индексе
        """
        create_result = self.bulk_create(index_name=index_name, items=items)

        already_exists_ids = set()
        for item_id, error in create_result:
            if error is not None and "document already exists" in error:
                already_exists_ids.add(item_id)

        if not already_exists_ids:
            return create_result

        update_result = self.bulk_update(
            index_name=index_name,
            items=[(item_id, item) for item_id, item in items if item_id in already_exists_ids],
        )

        errors_map = {
            **{item_id: error for item_id, error in create_result},
            **{item_id: error for item_id, error in update_result},
        }

        return [(item_id, errors_map.get(item_id)) for item_id, _ in items]


class BaseStorage:
    @abc.abstractmethod
    def save_state(self, state: dict) -> None:
        """Сохранить состояние в постоянное хранилище"""
        pass

    @abc.abstractmethod
    def retrieve_state(self) -> dict:
        """Загрузить состояние локально из постоянного хранилища"""
        pass


class JsonFileStorage(BaseStorage):
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def save_state(self, state: dict) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open(mode="w") as f:
            json.dump(state, f)

    def retrieve_state(self) -> dict:
        try:
            with self.file_path.open() as f:
                data = json.load(f)

            return data

        except (FileNotFoundError, json.JSONDecodeError):
            self.save_state({})
            return {}


class State:
    """
    Класс для хранения состояния при работе с данными, чтобы постоянно не перечитывать данные с начала.
    Здесь представлена реализация с сохранением состояния в файл.
    В целом ничего не мешает поменять это поведение на работу с БД или распределённым хранилищем.
    """

    def __init__(self, storage: BaseStorage):
        self.storage = storage
        self.state = self.retrieve_state()

    def retrieve_state(self) -> dict:
        data = self.storage.retrieve_state()
        return data

    def set_state(self, key: str, value: Any) -> None:
        """Установить состояние для определённого ключа"""
        self.state[key] = value
        self.storage.save_state(self.state)

    def get_state(self, key: str) -> Any:
        """Получить состояние по определённому ключу"""
        return self.state.get(key)
