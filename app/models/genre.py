from pydantic import UUID4, BaseModel

from core import json


class Genre(BaseModel):
    """Жанры."""

    id: UUID4
    name: str
    description = str

    class Config:
        json_loads = json.loads
        json_dumps = json.dumps
