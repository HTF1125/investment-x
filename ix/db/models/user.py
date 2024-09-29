from bunnet import Document
# from pydantic import BaseModel, EmailStr


class User(Document):
    # email: EmailStr
    password: str