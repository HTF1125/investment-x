"""
Authentication router for login, registration, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta

from ix.api.schemas import Token, UserLogin, UserRegister, UserResponse
from ix.api.dependencies import get_current_user
from ix.misc.auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_user_token,
)
from ix.db.models.user import User
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/auth/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Login endpoint - OAuth2 compatible.

    Can also accept JSON body with username (as email) and password.
    """
    # form_data.username contains the email
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use email as the identifier in the token
    access_token = create_user_token(str(user.email), bool(user.is_admin))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/login/json", response_model=Token)
async def login_json(credentials: UserLogin):
    """
    Login endpoint - JSON body format.

    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    """
    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_user_token(str(user.email), bool(user.is_admin))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """
    Register a new user.

    Request body:
    {
        "email": "user@example.com",
        "password": "password123",
        "first_name": "First", # optional
        "last_name": "Last"   # optional
    }
    """
    # Check if user already exists
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
            is_admin=False,
        )
        logger.info(f"New user registered: {user.email}")
        return UserResponse(
            id=str(user.id),
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            is_admin=bool(user.is_admin),
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
async def get_current_user_info(
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
        is_admin=bool(current_user.is_admin),
        disabled=bool(current_user.disabled),
        created_at=current_user.created_at,
    )


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token.
    """
    access_token = create_user_token(
        str(current_user.email), bool(current_user.is_admin)
    )
    return {"access_token": access_token, "token_type": "bearer"}
