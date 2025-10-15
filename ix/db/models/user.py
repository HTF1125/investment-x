from typing import Annotated, Optional
from bunnet import Document, Indexed
from ix.misc import get_logger
import bcrypt


logger = get_logger(__name__)


class User(Document):
    username: Annotated[str, Indexed(unique=True)]
    password: str  # Hashed password
    disabled: bool = False
    is_admin: bool = False
    email: Optional[str] = None
    created_at: Optional[str] = None

    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password"""
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @classmethod
    def get_user(cls, username: str) -> Optional["User"]:
        """Get user by username"""
        return cls.find_one(cls.username == username).run()

    @classmethod
    def new_user(
        cls,
        username: str,
        password: str,
        email: Optional[str] = None,
        is_admin: bool = False,
    ) -> "User":
        """Create a new user with hashed password"""
        from datetime import datetime

        hashed_password = cls.hash_password(password)
        return cls(
            username=username,
            password=hashed_password,
            email=email,
            is_admin=is_admin,
            created_at=datetime.utcnow().isoformat(),
        ).create()

    @classmethod
    def exists(cls, username: str) -> bool:
        """Check if user exists"""
        return cls.get_user(username=username) is not None
