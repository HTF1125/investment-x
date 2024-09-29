from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ix.db import User


router = APIRouter(
    prefix="/user",
    tags=["user"],
)

