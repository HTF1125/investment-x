"""





"""


from typing import Annotated
from datetime import date
from bunnet import Document, Indexed



class Regime(Document):
    code: Annotated[str, Indexed(unique=True)]
    data: dict[date, str] | None = {}
