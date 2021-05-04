import json
import logging
import os
from functools import wraps
from time import sleep
from typing import Callable

import requests
from requests.exceptions import ConnectionError, ConnectTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("etl")


def get_logger(name):
    return logging.getLogger(f"etl.{name}")


def coroutine(func):
    @wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn

    return inner


def backoff(
    on_predicate: Callable[[Exception], bool],
    start_sleep_time: float = 0.1,
    factor: int = 2,
    border_sleep_time: int = 10,
):
    """
    Функция для повторного выполнения функции через некоторое время, если
    возникла ошибка. Использует наивный экспоненциальный рост времени повтора
    (factor) до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * 2^(n) if t < border_sleep_time
        t = border_sleep_time if t >= border_sleep_time

    :param on_predicate:
    :param start_sleep_time: начальное время повтора
    :param factor: во сколько раз нужно увеличить время ожидания
    :param border_sleep_time: граничное время ожидания
    :return: результат выполнения функции

    """

    def func_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            current_sleep_time = start_sleep_time

            while True:
                try:
                    res = func(*args, **kwargs)
                    return res

                except Exception as e:
                    if not on_predicate(e):
                        raise e

                    logger.error(f"{e!r} sleep for {current_sleep_time}s")

                    sleep(current_sleep_time)

                    next_sleep_time = current_sleep_time * (2 ** factor)
                    current_sleep_time = (
                        next_sleep_time
                        if next_sleep_time <= border_sleep_time
                        else border_sleep_time
                    )

        return inner

    return func_wrapper


def load_indexes(es_dsn: str):
    """Функция для загрузки индексов в elastic"""

    @backoff(lambda exc: isinstance(exc, (ConnectionError, ConnectTimeout)))
    def create_if_not_exist(url, data):
        response = requests.head(url=url)
        if response.status_code == 404:
            requests.put(url=url, json=data)

    indexes = os.listdir("indexes")
    for index in indexes:
        with open(f"indexes/{index}") as infile:
            data = json.load(infile)
            index_name = index.split(".")[0]
            url = f"{es_dsn}{index_name}"
            create_if_not_exist(url, data)
