


from bunnet import Document


class EconomicCalendar(Document):
    date: str
    time: str
    event: str
    zone: str | None = None
    currency: str | None = None
    importance: str | None = None
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None
