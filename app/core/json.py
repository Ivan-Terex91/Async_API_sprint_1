import orjson

loads = orjson.loads


def dumps(v, *, default):
    return orjson.dumps(v, default=default).decode()
