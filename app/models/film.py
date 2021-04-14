from pydantic import BaseModel

from core import json


class Film(BaseModel):
    id: str
    title: str
    description: str

    class Config:
        # Заменяем стандартную работу с json на более быструю
        json_loads = json.loads
        json_dumps = json.dumps
