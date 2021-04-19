import pydantic

from core import json


class BaseModel(pydantic.BaseModel):
    class Config:
        # Заменяем стандартную работу с json на более быструю
        json_loads = json.loads
        json_dumps = json.dumps
