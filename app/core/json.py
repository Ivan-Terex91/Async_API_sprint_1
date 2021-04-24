import orjson

loads = orjson.loads


def dumps(v):
    return orjson.dumps(v).decode()
