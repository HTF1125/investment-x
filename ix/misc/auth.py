"""
Authentication utilities for JWT token management and session handling
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
from ix.misc import get_logger
from typing import cast

logger = get_logger(__name__)

# Secret key for JWT - In production, this should be an environment variable
SECRET_KEY = (
    "your-secret-key-change-this-in-production"  # TODO: Move to environment variable
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary containing user data to encode
        expires_delta: Optional timedelta for token expiration

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token data if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def authenticate_user(email: str, password: str):
    """
    Authenticate a user with email and password against the SQL database.

    Returns:
        The User ORM instance on success, otherwise None.
    """
    try:
        # Import lazily to avoid circular imports at module import time
        from ix.db.models.user import User

        user = User.get_by_email(email)
        if not user:
            logger.warning(f"User not found: {email}")
            return None

        if getattr(user, "disabled", False):
            logger.warning(f"User is disabled: {email}")
            return None

        if not user.verify_password(password):
            logger.warning(f"Invalid password for user: {email}")
            return None
        return user
    except Exception as exc:
        logger.exception(f"authenticate_user error: {exc}")
        return None


def get_current_user(token: str):
    """
    Resolve the current user from a JWT token.
    Returns the User ORM instance if token is valid and user exists; otherwise None.
    """
    try:
        from ix.db.models.user import User

        payload = verify_token(token)
        if not payload:
            return None
        email = cast(Optional[str], payload.get("sub"))
        if not email:
            return None
        user = User.get_by_email(email)
        if not user or getattr(user, "disabled", False):
            return None
        return user
    except Exception as exc:
        logger.exception(f"get_current_user error: {exc}")
        return None


def create_user_token(
    email: str,
    role: str = "general",
    is_admin: Optional[bool] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT token for a user

    Args:
        email: User email
        role: Role string (owner/admin/general)
        is_admin: Optional compatibility flag; if omitted it is derived from role
        expires_delta: Optional timedelta for token expiration

    Returns:
        JWT token string
    """
    resolved_role = (role or "").strip().lower() or "general"
    resolved_is_admin = (
        is_admin
        if is_admin is not None
        else resolved_role in {"owner", "admin"}
    )
    token_data = {
        "sub": email,
        "role": resolved_role,
        "is_admin": bool(resolved_is_admin),  # keep for backward compatibility
        "iat": datetime.utcnow(),
    }

    return create_access_token(token_data, expires_delta=expires_delta)
