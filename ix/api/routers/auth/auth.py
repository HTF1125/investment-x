"""
Authentication router for login, registration, and token management.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta

from ix.api.schemas import Token, UserLogin, UserRegister, UserResponse
from ix.api.dependencies import get_current_user
from ix.misc.auth import (
    authenticate_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_user_token,
    verify_token_allow_expired,
)
from ix.db.models.user import User
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()

_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")

from fastapi import Request
from ix.api.rate_limit import limiter as _limiter


def set_auth_cookie(
    response: Response, token: str, expires_delta: timedelta | None = None
):
    """Utility to set the JWT cookie."""
    max_age = (
        int(expires_delta.total_seconds())
        if expires_delta
        else ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        samesite="lax",
        secure=_COOKIE_SECURE,
        path="/",
    )


@router.post("/auth/login", response_model=Token)
@_limiter.limit("5/minute")
def login(
    request: Request, response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    Login endpoint - OAuth2 compatible.
    Sets HttpOnly cookie for SSR support.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_user_token(
        str(user.email),
        role=getattr(user, "effective_role", User.ROLE_GENERAL),
    )
    set_auth_cookie(response, access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/login/json", response_model=Token)
@_limiter.limit("5/minute")
def login_json(request: Request, response: Response, credentials: UserLogin):
    """
    Login endpoint - JSON body format.
    Sets HttpOnly cookie for SSR support.
    """
    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_delta = timedelta(days=30) if credentials.remember_me else None
    access_token = create_user_token(
        str(user.email),
        role=getattr(user, "effective_role", User.ROLE_GENERAL),
        expires_delta=expires_delta,
    )
    set_auth_cookie(response, access_token, expires_delta=expires_delta)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/logout")
def logout(response: Response):
    """
    Logout endpoint - clears the HttpOnly cookie.
    """
    response.delete_cookie(key="access_token", path="/", samesite="lax")
    return {"message": "Successfully logged out"}


@router.post("/auth/register", response_model=UserResponse)
@_limiter.limit("3/minute")
def register(request: Request, user_data: UserRegister):
    """
    Register a new user.
    """
    if User.exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        user = User.new_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=User.ROLE_GENERAL,
        )
        logger.info(f"New user registered: {user.email}")
        role = getattr(user, "effective_role", User.ROLE_GENERAL)
        return UserResponse(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            role=role,
            is_admin=bool(role in User.ADMIN_ROLES),
            disabled=bool(user.disabled),
            created_at=user.created_at,
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=str(current_user.id),
        email=str(current_user.email),
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.effective_role,
        is_admin=bool(current_user.effective_role in User.ADMIN_ROLES),
        disabled=bool(current_user.disabled),
        created_at=current_user.created_at,
    )


@router.post("/auth/refresh", response_model=Token)
@_limiter.limit("10/minute")
def refresh_token(request: Request, response: Response):
    """
    Refresh access token and update cookie.
    Accepts recently-expired tokens (within 7 days) so sessions can be
    silently renewed without forcing a re-login.
    """
    # Extract token from header or cookie
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer") else None
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token_allow_expired(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token invalid or expired beyond refresh window")

    user = User.get_by_email(payload["sub"])
    if not user or getattr(user, "disabled", False):
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access_token = create_user_token(
        str(user.email),
        role=user.effective_role,
    )
    set_auth_cookie(response, access_token)
    return {"access_token": access_token, "token_type": "bearer"}
