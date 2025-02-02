from fastapi import Depends, HTTPException, status, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter
from ix import db
from ix.misc.settings import Settings

# App setup
router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing
crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    isadmin: bool = False
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

# Database interaction
def get_user(username: str) -> Optional[db.User]:
    """
    Fetch user details from the database by username.
    """
    try:
        user = db.User.get_user(username=username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user
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
    if not user or not verify_password(password, user.password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with expiration.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=Settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Settings.secret_key, algorithm=Settings.algorithm)

async def get_current_user(authorization: Optional[str] = Header(None)) -> db.User:
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
            token, Settings.secret_key, algorithms=[Settings.algorithm]
        )
        username: str = payload["sub"]
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: db.User = Depends(get_current_user),
) -> db.User:
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
async def get_token(user: UserIn):
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

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: db.User = Depends(get_current_active_user)):
    """
    Refresh the access token if it's expired.
    """
    access_token_expires = timedelta(minutes=Settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=db.User)
async def read_users_me(current_user: db.User = Depends(get_current_active_user)):
    """
    Retrieve the currently logged-in user details.
    """
    return current_user

# Create User Endpoint
@router.post("/create", response_model=db.User)
async def create_user(user: UserIn):
    """
    Register a new user.
    """
    # Check if the username already exists
    if db.User.exists(username=user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user.password)

    # Create the user and save to the database
    new_user = db.User(username=user.username, password=hashed_password)
    try:
        return new_user.create()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}",
        )
