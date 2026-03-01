"""
FastAPI dependencies for authentication and database.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from sqlalchemy.orm import Session as SessionType
from ix.misc.auth import verify_token
from ix.db.models.user import User
from ix.db.conn import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db():
    """Dependency to get database session."""
    with Session() as session:
        yield session


from fastapi import Request


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """
    Dependency to get current authenticated user.
    Supports both Header (Authorization: Bearer X) and Cookie (access_token=X).
    """
    # 1. Check Header (via token param, already handled by oauth2_scheme if present)
    # 2. Check Cookie if Header is missing
    # 3. Check Query Param if Cookie is missing (for native form downloads)
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: Optional[str] = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = User.get_by_email(email)
    if not user or getattr(user, "disabled", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, or None if not.
    Does not raise on missing/invalid credentials.
    """
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        token = request.query_params.get("token")
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    email: Optional[str] = payload.get("sub")
    if not email:
        return None
    user = User.get_by_email(email)
    if not user or getattr(user, "disabled", False):
        return None
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current authenticated admin user.

    Raises:
        HTTPException: If user is not an admin
    """
    role = getattr(current_user, "effective_role", None)
    if callable(role):
        role = role()
    if role is None:
        role = User.normalize_role(getattr(current_user, "role", None))
    if role not in User.ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
