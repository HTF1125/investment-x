"""
Shared rate limiter instance for all routers.

Import `limiter` from this module instead of creating per-router instances,
so that rate limits are tracked globally per client IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
