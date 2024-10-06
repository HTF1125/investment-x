"""





"""


from typing import Annotated
from datetime import date
from pydantic import BaseModel
from bunnet import Document, Indexed


class Data(BaseModel):

    d: list[date]
    v: list[float]
    l: list[float]
    s: list[dict[str, float]]
    c: list[dict[str, float]]
    w: list[dict[str, float]]
    a: list[dict[str, float]]


class Strategy(Document):

    code: Annotated[str, Indexed(unique=True)]
    data: Data
