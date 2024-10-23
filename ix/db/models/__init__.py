import sys
import inspect
from bunnet import Document

# Import all modules (keep these imports)
from .ticker import *
from .strategy import *
from .regime import *
from .economic_calendar import *
from .user import *
from .insight import *

def all_models():
    """
    Dynamically returns a list of all document models for easy reference.
    """
    current_module = sys.modules[__name__]

    models = []
    for _, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, Document) and obj != Document:
            models.append(obj)

    return models
