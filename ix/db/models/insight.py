from typing import Annotated
from datetime import date
from pydantic import BaseModel
from bunnet import Document, Indexed


class InsightKeyInfo(BaseModel):
    date: Annotated[date, Indexed()]
    title: str
    tags: list[str] = []


class Insight(Document):
    date: Annotated[date, Indexed()]
    title: str
    tags: list[str] = []
    content: str
