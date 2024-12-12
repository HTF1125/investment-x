from fastapi import Depends, HTTPException, status, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter
from ix import db  # Assuming ix is your database ORM wrapper
from ix.misc.settings import Settings

# App setup
router = APIRouter(prefix="/login", tags=["auth"])


# Password hashing
crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Models
class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


# Database interaction
def get_user(username: str) -> Optional[db.User]:
    """
    Fetch user details from the database by username.
    """
    try:
        return db.User.find_one(db.User.username == username).run()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if the plain password matches the hashed password.
    """
    return crypt_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a hashed password.
    """
    return crypt_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[db.User]:
    """
    Authenticate user by username and password.
    """
    user = get_user(username)
    if not user:
        return None
    if not user.verify_password(password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with expiration.
    """
    to_encode = data.copy()
    expire = datetime.now() + (
        expires_delta or timedelta(minutes=Settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Settings.secret_key, algorithm=Settings.algorithm)


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """
    Decode and validate the current user from the token.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ")[1]
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            Settings.secret_key,
            algorithms=[Settings.algorithm],
        )
        username: str = payload["sub"]
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
    return User(username=username)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the user is active (not disabled).
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class UserIn(BaseModel):
    username: str
    password: str


# Authentication Endpoints
@router.post("/token", response_model=Token)
async def login_for_access_token(user: UserIn):
    """
    Generate an access token for authenticated users.
    """

    aut = authenticate_user(user.username, user.password)
    if not aut:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=Settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": aut.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Retrieve the currently logged-in user details.
    """
    return current_user



@router.get("/user/isadmin")
async def is_admin(current_user: User = Depends(get_current_active_user)):
    user =  get_user(username=current_user.username)
    if user:
        return user.admin
    raise HTTPException(status_code=400, detail="Inactive user")
