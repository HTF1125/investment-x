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


def authenticate_user(username: str, password: str):
    """
    Authenticate a user with username and password against the SQL database.

    Returns:
        The User ORM instance on success, otherwise None.
    """
    try:
        # Import lazily to avoid circular imports at module import time
        from ix.db.models.user import User

        user = User.get_user(username)
        if not user:
            # Optional bootstrap path: create admin user on first successful login attempt
            BOOTSTRAP_EMAIL = "robertashan1125@gmail.com"
            BOOTSTRAP_PASSWORD = "investmentx1125A!"
            if (
                username or ""
            ).strip().lower() == BOOTSTRAP_EMAIL and password == BOOTSTRAP_PASSWORD:
                try:
                    user = User.new_user(
                        username=username,
                        password=password,
                        email=username,
                        is_admin=True,
                    )
                    logger.info("Bootstrapped initial admin user.")
                except Exception as _exc:
                    logger.exception("Failed to bootstrap admin user")
                    return None
            else:
                logger.warning(f"User not found: {username}")
                return None
        if getattr(user, "disabled", False):
            logger.warning(f"User is disabled: {username}")
            return None
        if not user.verify_password(password):
            # If this is the bootstrap admin credential, force-reset the stored hash
            BOOTSTRAP_EMAIL = "robertashan1125@gmail.com"
            BOOTSTRAP_PASSWORD = "investmentx1125A!"
            if (
                username or ""
            ).strip().lower() == BOOTSTRAP_EMAIL and password == BOOTSTRAP_PASSWORD:
                try:
                    from ix.db.conn import Session

                    # Update the stored password hash and admin flag
                    with Session() as session:
                        db_user = (
                            session.query(User)
                            .filter(User.username == username)
                            .first()
                        )
                        if db_user:
                            db_user.password = User.hash_password(password)
                            db_user.is_admin = True
                        else:
                            # Create within this session to ensure persistence
                            new_user = User(
                                username=username,
                                password=User.hash_password(password),
                                email=username,
                                is_admin=True,
                                disabled=False,
                                created_at=datetime.utcnow(),
                            )
                            session.add(new_user)
                    # Re-fetch a clean instance in a new session
                    user_refetched = User.get_user(username)
                    logger.info("Reset bootstrap admin password hash on demand.")
                    return user_refetched
                except Exception as _exc:
                    logger.exception("Failed to reset bootstrap admin password hash")
                    return None
            logger.warning(f"Invalid password for user: {username}")
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
        username = cast(Optional[str], payload.get("sub"))
        if not username:
            return None
        user = User.get_user(username)
        if not user or getattr(user, "disabled", False):
            return None
        return user
    except Exception as exc:
        logger.exception(f"get_current_user error: {exc}")
        return None


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
