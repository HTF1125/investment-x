from sqlalchemy import Column, String, Boolean, DateTime, text, func
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
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # Hashed password
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    disabled = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=True)

    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password"""
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @classmethod
    def get_by_email(cls, email: str):
        """Fetch user by email (case-insensitive), ensuring all attributes are loaded."""
        from ix.db.conn import Session

        if not email:
            return None

        # Normalize input
        email_clean = email.strip().lower()

        with Session() as session:
            # Case-insensitive lookup using func.lower()
            user = (
                session.query(cls).filter(func.lower(cls.email) == email_clean).first()
            )
            if user:
                # Force load all columns to avoid DetachedInstanceError
                for column in cls.__table__.columns:
                    getattr(user, column.name)
                session.expunge(user)
            return user

    @classmethod
    def new_user(
        cls,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_admin: bool = False,
    ):
        """Create a new user with hashed password"""
        from ix.db.conn import Session

        hashed_password = cls.hash_password(password)
        # Always store email as lowercase for consistency
        user = cls(
            email=email.strip().lower(),
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            created_at=datetime.utcnow(),
        )

        with Session() as session:
            session.add(user)
            session.flush()
            session.refresh(user)
            # Force load all columns
            for column in cls.__table__.columns:
                getattr(user, column.name)
            session.expunge(user)
            return user

    @classmethod
    def exists(cls, email: str) -> bool:
        """Check if user exists by email"""
        return cls.get_by_email(email=email) is not None
