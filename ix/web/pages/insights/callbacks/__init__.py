"""Callbacks for Insights page - organized by functionality."""

# Import all callbacks to register them
from .data_callbacks import *  # noqa: F403, F401
from .filter_callbacks import *  # noqa: F403, F401
from .action_callbacks import *  # noqa: F403, F401
from .row_click import *  # noqa: F403, F401

# Import other callbacks that may exist
try:
    from .upload import *  # noqa: F403, F401
except ImportError:
    pass

try:
    from .publishers import *  # noqa: F403, F401
except ImportError:
    pass
