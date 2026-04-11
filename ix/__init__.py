"""Investment-X backend package. See ARCHITECTURE.md for module placement guide."""

from . import core
from . import common
from .core import backtesting as bt
from .db.query import *
from .db.client import *
from .core.indicators import *
from .collectors import crawler
from .common.viz.theme import apply_research_style, NBER_RECESSIONS
from .core import indicators, regimes
from . import collectors