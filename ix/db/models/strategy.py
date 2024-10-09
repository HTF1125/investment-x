from typing import Annotated
from pydantic import BaseModel, field_validator
from bunnet import Document, Indexed
import numpy as np

class Book(BaseModel):
    d: list[str] = []
    v: list[float] = []
    l: list[float] = []
    b: list[float] = []
    s: list[dict[str, float]] = []
    c: list[dict[str, float]] = []
    w: list[dict[str, float]] = []
    a: list[dict[str, float]] = []

class StrategySummary(BaseModel):
    code: Annotated[str, Indexed(unique=True)]
    last_updated: str | None = None
    ann_return: float | None = None
    ann_volatility: float | None = None
    nav_history: list[float] | None = None

class Strategy(StrategySummary, Document):
    book: Book = Book()

    @field_validator('last_updated', 'ann_return', 'ann_volatility', 'nav_history', mode='before')
    @classmethod
    def update_summary(cls, v, info):
        book = info.data.get('book', Book())
        if book.d:
            info.data['last_updated'] = book.d[-1]
        if book.v:
            info.data['nav_history'] = book.v[-30:]  # Last 30 days
            if len(book.v) > 1:
                info.data['ann_return'] = (book.v[-1] / book.v[0]) - 1
                returns = np.diff(book.v) / book.v[:-1]
                info.data['ann_volatility'] = np.std(returns) * np.sqrt(252)
            else:
                info.data['ann_return'] = 0.0
                info.data['ann_volatility'] = 0.0
        return v

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)