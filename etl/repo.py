from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from itertools import chain
from typing import Any, Dict, Iterator, List, Set

from storage import ElasticWriter, PGReader
from utils import logger

from models import Filmwork, FilmworkIDType, FilmworkPerson, Genre, Person


class BaseRepository(ABC):
    """
    Базовый класс для описания запросов к postgres, elastic в рамках конкретной модели данных
    """

    def __init__(self, pg_reader: PGReader, elastic_writer: ElasticWriter):
        self.pg_reader = pg_reader
        self.elastic_writer = elastic_writer

    @abstractmethod
    def get_modified_items(
        self, last_timestamp: datetime, chunk_size: int = 100
    ) -> Iterator[List[Any]]:
        """
        Метод для получения данных, обновленных после last_timestamp
        """
        pass

    @abstractmethod
    def update_items_index(self, items: List[Any]):
        """
        Метод для обновления документов в индексе
        """
        pass


class GenreRepository(BaseRepository):
    def get_modified_items(
        self, last_timestamp: datetime, chunk_size: int = 100
    ) -> Iterator[List[Genre]]:
        offset = 0
        while items := self.pg_reader.read_modified_genres(last_timestamp, offset, chunk_size):
            offset += len(items)
            yield [Genre(id=genre_id, name=name) for genre_id, name in items]

    def update_items_index(self, items: List[Genre]) -> None:
        result = self.elastic_writer.bulk_create_or_update(
            index_name="genres", items=[(i.id, i.to_dict()) for i in items]
        )
        for item_id, error in result:
            if error:
                logger.error(f'Update for genre document "{item_id}" got error "{error}".')

        return None


class PersonRepository(BaseRepository):
    def get_modified_items(
        self, last_timestamp: datetime, chunk_size: int = 100
    ) -> Iterator[List[Person]]:
        offset = 0
        while items := self.pg_reader.read_modified_persons(last_timestamp, offset, chunk_size):
            offset += len(items)
            yield [
                Person(id=person_id, full_name=f"{first_name} {last_name}")
                for person_id, first_name, last_name in items
            ]

    def update_items_index(self, items: List[Person]) -> None:
        result = self.elastic_writer.bulk_create_or_update(
            index_name="persons", items=[(i.id, i.to_dict()) for i in items]
        )
        for item_id, error in result:
            if error:
                logger.error(f'Update for person document "{item_id}" got error "{error}".')

        return None


class FilmworkRepository(BaseRepository):
    def get_modified_items(
        self, last_timestamp: datetime, chunk_size: int = 100
    ) -> Iterator[List[Filmwork]]:
        """
        Получение списка обновленных фильмов. id обновленных фильмов собираются из 3 источников:
        1. Непосредственно обновленные фильмы
        2. Обновленные жанры
        3. Обновленные участники

        Чтобы исключить дублирование id фильмов обработанные id записываются в unique_ids.
        Данные о фильмах возвращаются пачками по chunk_size записей.
        """
        unique_ids: Set[FilmworkIDType] = set()
        chunk_filmwork_ids: List[FilmworkIDType] = []

        for possible_filmwork_ids in chain(
            self._get_modified_filmworks(last_timestamp, limit=chunk_size),
            self._get_modified_filmworks_from_genres(last_timestamp, limit=chunk_size),
            self._get_modified_filmworks_from_persons(last_timestamp, limit=chunk_size),
        ):
            for filmwork_id in possible_filmwork_ids:
                if filmwork_id in unique_ids:
                    continue

                unique_ids.add(filmwork_id)
                chunk_filmwork_ids.append(filmwork_id)

                if len(chunk_filmwork_ids) >= chunk_size:
                    yield self.get_filmworks(chunk_filmwork_ids)
                    chunk_filmwork_ids = []

        if chunk_filmwork_ids:
            yield self.get_filmworks(chunk_filmwork_ids)

    def _get_modified_filmworks(
        self, last_timestamp: datetime, limit: int
    ) -> Iterator[List[FilmworkIDType]]:
        offset = 0
        while filmwork_ids := self.pg_reader.read_modified_filmworks(last_timestamp, offset, limit):
            offset += len(filmwork_ids)
            yield filmwork_ids

    def _get_modified_filmworks_from_genres(
        self, last_timestamp: datetime, limit: int
    ) -> Iterator[List[FilmworkIDType]]:
        offset = 0
        while filmwork_ids := self.pg_reader.read_modified_filmworks_from_genres(
            last_timestamp, offset, limit
        ):
            offset += len(filmwork_ids)
            yield filmwork_ids

    def _get_modified_filmworks_from_persons(
        self, last_timestamp: datetime, limit: int
    ) -> Iterator[List[FilmworkIDType]]:
        offset = 0
        while filmwork_ids := self.pg_reader.read_modified_filmworks_from_persons(
            last_timestamp, offset, limit
        ):
            offset += len(filmwork_ids)
            yield filmwork_ids

    def get_filmworks(self, filmworks_ids: List[FilmworkIDType]) -> List[Filmwork]:
        filmworks = []
        for id, filmwork_type, title, description, rating, genres in self.pg_reader.read_filmworks(
            filmworks_ids
        ):
            filmworks.append(
                Filmwork(
                    id=id,
                    filmwork_type=filmwork_type,
                    title=title,
                    description=description,
                    imdb_rating=rating,
                )
            )
        return filmworks

    def get_filmworks_participants(
        self, filmworks_ids: List[FilmworkIDType]
    ) -> Dict[FilmworkIDType, List[FilmworkPerson]]:
        """
        Получение участников фильмов
        """
        filmworks_to_participans_map: Dict[FilmworkIDType, FilmworkPerson] = defaultdict(list)
        for (
            filmwork_id,
            person_id,
            first_name,
            last_name,
            role,
        ) in self.pg_reader.read_filmworks_participants(filmworks_ids):
            filmworks_to_participans_map[filmwork_id].append(
                FilmworkPerson(id=person_id, full_name=f"{first_name} {last_name}", role=role)
            )
        return filmworks_to_participans_map

    def get_filmworks_genres(
        self, filmworks_ids: List[FilmworkIDType]
    ) -> Dict[FilmworkIDType, List[Genre]]:
        """
        Получение жанров фильмов
        """
        filmworks_to_genres_map: Dict[FilmworkIDType, Genre] = defaultdict(list)
        for (filmwork_id, genre_id, name) in self.pg_reader.read_filmworks_genres(filmworks_ids):
            filmworks_to_genres_map[filmwork_id].append(Genre(id=genre_id, name=name))
        return filmworks_to_genres_map

    def update_items_index(self, items: List[Filmwork]) -> None:
        result = self.elastic_writer.bulk_create_or_update(
            index_name="movies", items=[(i.id, i.to_dict()) for i in items]
        )
        for item_id, error in result:
            if error:
                logger.error(f'Update for movies document "{item_id}" got error "{error}".')

        return None
