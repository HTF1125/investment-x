from sqlalchemy import Column, String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
from datetime import datetime
import bcrypt
from ix.db.conn import Base


class User(Base):
    """User model for PostgreSQL."""

    __tablename__ = "user"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # Hashed password
    disabled = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)

    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password"""
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @classmethod
    def get_user(cls, username: str):
        """Get user by username"""
        from ix.db.conn import Session

        with Session() as session:
            return session.query(cls).filter(cls.username == username).first()

    @classmethod
    def new_user(
        cls,
        username: str,
        password: str,
        email: Optional[str] = None,
        is_admin: bool = False,
    ):
        """Create a new user with hashed password"""
        from ix.db.conn import Session

        hashed_password = cls.hash_password(password)
        user = cls(
            username=username,
            password=hashed_password,
            email=email,
            is_admin=is_admin,
            created_at=datetime.utcnow(),
        )

        with Session() as session:
            session.add(user)
            # Ensure the instance is persisted before refresh in SQLAlchemy 2.x
            session.flush()
            session.refresh(user)
            return user

    @classmethod
    def exists(cls, username: str) -> bool:
        """Check if user exists"""
        return cls.get_user(username=username) is not None
