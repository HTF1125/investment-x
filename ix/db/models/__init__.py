

from .ticker import Ticker, TickerNew
from .strategy import Strategy
from .regime import Regime
from .economic_calendar import EconomicCalendar
from .user import *


def all_models():
    """
    Returns a list of all document models for easy reference.
    """
    return [
        Ticker,
        TickerNew,
        EconomicCalendar,
        Strategy,
        Regime,
        User,
    ]

