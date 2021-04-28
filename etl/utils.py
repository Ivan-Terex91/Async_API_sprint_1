import logging
from functools import wraps
from time import sleep
from typing import Callable

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
