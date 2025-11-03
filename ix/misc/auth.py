"""
Authentication utilities for JWT token management and session handling
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
from ix.misc import get_logger

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


def authenticate_user(username: str, password: str):
    """
    Authenticate a user with username and password

    Args:
        username: Username
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    # from ix.db.models import User  # Commented out - MongoDB not in use
    return None  # Authentication disabled - MongoDB not in use

    user = User.get_user(username)

    if not user:
        logger.warning(f"User not found: {username}")
        return None

    if user.disabled:
        logger.warning(f"User is disabled: {username}")
        return None

    if not user.verify_password(password):
        logger.warning(f"Invalid password for user: {username}")
        return None

    return user


def get_current_user(token: str):
    """
    Get the current user from a JWT token

    Args:
        token: JWT token string

    Returns:
        User object if token is valid and user exists, None otherwise
    """
    # from ix.db.models import User  # Commented out - MongoDB not in use
    return None  # Authentication disabled - MongoDB not in use

    payload = verify_token(token)

    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    user = User.get_user(username)

    if not user or user.disabled:
        return None

    return user


def create_user_token(username: str, is_admin: bool = False) -> str:
    """
    Create a JWT token for a user

    Args:
        username: Username
        is_admin: Whether the user is an admin

    Returns:
        JWT token string
    """
    token_data = {"sub": username, "is_admin": is_admin, "iat": datetime.utcnow()}

    return create_access_token(token_data)
