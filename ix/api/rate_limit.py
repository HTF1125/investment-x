"""
Shared rate limiter instance for all routers.

Import `limiter` from this module instead of creating per-router instances,
so that rate limits are tracked globally per client IP.

Admin and owner users are exempt from all rate limits.  The custom key
function returns an empty string for those roles, which causes slowapi to
skip the limit check entirely (its internal `all(args)` guard).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

# Roles exempt from rate limiting
_EXEMPT_ROLES = {"owner", "admin"}


def _rate_limit_key(request: Request) -> str:
    """Return the rate-limit key for a request.

    For admin/owner users (identified via JWT in the Authorization header or
    access_token cookie), return an empty string so slowapi skips the limit.
    For all other users, fall back to the remote IP address.
    """
    try:
        token = None
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        if not token:
            token = request.cookies.get("access_token")
        if token:
            # Inline decode to avoid circular imports and keep this lightweight.
            # We only need the role claim; full auth validation happens in the
            # route dependency.  We import lazily to avoid import-time side
            # effects (SECRET_KEY validation happens at import of ix.common.auth).
            import jwt as _jwt
            from ix.common.security.auth import SECRET_KEY, ALGORITHM

            payload = _jwt.decode(
                token, SECRET_KEY, algorithms=[ALGORITHM],
                options={"verify_exp": True},
            )
            role = (payload.get("role") or "").lower()
            if role in _EXEMPT_ROLES:
                return ""
    except Exception:
        pass  # Fall back to IP-based or API-key-based rate limiting

    # Check X-API-Key header (no DB lookup — just hash for identity)
    api_key_raw = request.headers.get("x-api-key")
    if api_key_raw:
        import hashlib

        key_hash = hashlib.sha256(api_key_raw.encode()).hexdigest()
        return f"apikey:{key_hash[:16]}"

    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
