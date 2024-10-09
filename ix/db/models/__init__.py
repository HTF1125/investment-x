

from .ticker import Ticker
from .strategy import Strategy, StrategySummary
from .regime import Regime
from .economic_calendar import EconomicCalendar
from .user import *


def all_models():
    """
    Returns a list of all document models for easy reference.
    """
    return [
        Ticker,
        EconomicCalendar,
        Strategy,
        Regime,
        User,
    ]

