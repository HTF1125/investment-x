from fastapi import APIRouter, status
from ix.db import User


router = APIRouter(
    prefix="/user",
    tags=["user"],
)


@router.post(
    path="/signup",
    status_code=status.HTTP_201_CREATED
)
def create_user(user: User):

    return


