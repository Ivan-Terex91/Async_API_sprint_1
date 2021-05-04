from datetime import datetime
from time import sleep
from typing import Callable, List

from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn
from repo import BaseRepository, FilmworkRepository, GenreRepository, PersonRepository
from storage import ElasticWriter, JsonFileStorage, PGReader, State
from utils import coroutine, get_logger, load_indexes, logger

from models import Filmwork


class Settings(BaseSettings):
    elastic_dsn: AnyHttpUrl
    postgres_dsn: PostgresDsn
    local_storage_path: str = "/var/lib/ymp/etl.json"
    chunk_size: int = 100


def beat_coro(
    get_last_timestamp: Callable[[], datetime],
    set_last_timestamp: Callable[[datetime], None],
    consumers_coro,
):
    """
    Корутина для запуска процесса etl.
    1. Получает последнее время синхронизации данных
    2. Передает время обновлении другим корутинам для получения списка обновленных фильмов
    3. После успешной загрузки данных в elastic обновляет последнее время синхронизации
    """
    while True:
        new_timestamp = datetime.utcnow()
        last_timestamp = get_last_timestamp()
        logger.info(f'Starting etl process for last timestamp "{last_timestamp}"')

        for consumer in consumers_coro:
            consumer.send(last_timestamp)

        logger.info(f'Set new last timestamp to "{new_timestamp}"')
        set_last_timestamp(new_timestamp)

        sleep(10)


class BaseEtl:
    """
    Базовый класс для описания etl процесса
    """

    etl_name: str = ""

    def __init__(self, repo: BaseRepository, chunk_size: int = 100):
        self.repo = repo
        self.chunk_size = chunk_size
        self.logger = get_logger(self.etl_name)

    def get_pipeline(self):
        """
        Формирует корутину для обработки etl пайплайна
        """
        # Обновление данных в индексе
        update_index_coro = self.update_items_index()
        # Добавление недостающих данных
        enrich_items_coro = self.enrich_items(consumer=update_index_coro)
        # Получение обновленных данных
        get_modified_items_coro = self.get_modified_items(consumer=enrich_items_coro)
        return get_modified_items_coro

    @coroutine
    def get_modified_items(self, consumer):
        while last_timestamp := (yield):
            for items in self.repo.get_modified_items(last_timestamp, chunk_size=self.chunk_size):
                consumer.send(items)

    @coroutine
    def enrich_items(self, consumer):
        while items := (yield):
            enriched_items = self.enrich_items_chunk(items)
            consumer.send(enriched_items)

    @coroutine
    def update_items_index(self):
        while items := (yield):
            self.repo.update_items_index(items)
            self.logger.info(f'Updated index for "{len(items)}" items.')

    def enrich_items_chunk(self, items):
        return items


class GenreEtl(BaseEtl):
    etl_name = "genre"


class PersonEtl(BaseEtl):
    etl_name = "person"


class FilmworkEtl(BaseEtl):
    etl_name = "filmwork"

    def enrich_items_chunk(self, items: List[Filmwork]):
        filmworks_ids = [f.id for f in items]
        filmworks_participants_map = self.repo.get_filmworks_participants(filmworks_ids)
        filmworks_genres_map = self.repo.get_filmworks_genres(filmworks_ids)

        enriched_filmworks = []
        for filmwork in items:
            for person in filmworks_participants_map.get(filmwork.id, []):
                acc_field = {
                    "director": filmwork.directors,
                    "writer": filmwork.writers,
                    "actor": filmwork.actors,
                }[person.role]
                acc_field.append({"id": person.id, "full_name": person.full_name})

            filmwork.genres = filmworks_genres_map.get(filmwork.id, [])
            enriched_filmworks.append(filmwork)

        return enriched_filmworks


def main():
    settings = Settings()
    load_indexes(es_dsn=settings.elastic_dsn)
    # Клиенты для хранилищ
    state_storage = State(JsonFileStorage(str(settings.local_storage_path)))
    pg_reader = PGReader(str(settings.postgres_dsn))
    elastic_writer = ElasticWriter(str(settings.elastic_dsn))

    # Репозитории моделей для получения и обновления данных
    genre_repo = GenreRepository(pg_reader=pg_reader, elastic_writer=elastic_writer)
    person_repo = PersonRepository(pg_reader=pg_reader, elastic_writer=elastic_writer)
    filmwork_repo = FilmworkRepository(pg_reader=pg_reader, elastic_writer=elastic_writer)

    # Etl пайплайны для жанров, персонажей, фильмов
    genre_etl = GenreEtl(repo=genre_repo, chunk_size=settings.chunk_size)
    person_etl = PersonEtl(repo=person_repo, chunk_size=settings.chunk_size)
    filmwork_etl = FilmworkEtl(repo=filmwork_repo, chunk_size=settings.chunk_size)

    genre_pipeline = genre_etl.get_pipeline()
    person_pipeline = person_etl.get_pipeline()
    filmwork_pipeline = filmwork_etl.get_pipeline()

    def last_timestamp_getter() -> datetime:
        last_timestampt = state_storage.get_state("timestamp")
        if last_timestampt:
            return datetime.fromisoformat(last_timestampt)

        return datetime.min

    def last_timestamp_setter(timestamp: datetime):
        state_storage.set_state("timestamp", timestamp.isoformat())

    # Корутина для запуска процесса ETL
    beat_coro(
        get_last_timestamp=last_timestamp_getter,
        set_last_timestamp=last_timestamp_setter,
        consumers_coro=[genre_pipeline, person_pipeline, filmwork_pipeline],
    )


if __name__ == "__main__":
    main()
