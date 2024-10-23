from typing import Annotated
from pydantic import BaseModel
from bunnet import Document, Indexed

class Book(BaseModel):
    d: list[str] = []
    v: list[float] = []
    l: list[float] = []
    b: list[float] = []
    s: list[dict[str, float]] = []
    c: list[dict[str, float]] = []
    w: list[dict[str, float]] = []
    a: list[dict[str, float]] = []



class Strategy(Document):
    code: Annotated[str, Indexed(unique=True)]
    last_updated: str | None = None
    ann_return: float | None = None
    ann_volatility: float | None = None
    nav_history: list[float] | None = None
    book: Book = Book()

