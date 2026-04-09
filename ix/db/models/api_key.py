"""API Key model for programmatic access."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text, func
from sqlalchemy.dialects.postgresql import UUID

from ix.db.conn import Base
from ix.common import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "ix_"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, default="Default")
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(8), nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    @classmethod
    def create_key(cls, user_id: str, name: str = "Default") -> Tuple["ApiKey", str]:
        """Generate a new API key. Returns (ApiKey, raw_key). Raw key is shown once."""
        from ix.db.conn import Session

        raw_key = _KEY_PREFIX + secrets.token_hex(24)
        key_hash = _hash_key(raw_key)
        key_prefix = raw_key[:8]

        api_key = cls(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            created_at=datetime.now(timezone.utc),
        )

        with Session() as session:
            session.add(api_key)
            session.flush()
            session.refresh(api_key)
            for col in cls.__table__.columns:
                getattr(api_key, col.name)
            session.expunge(api_key)

        return api_key, raw_key

    @classmethod
    def get_user_by_key_hash(cls, raw_key: str) -> Optional["User"]:
        """Look up a non-revoked key and return the associated User. Updates last_used_at."""
        from ix.db.conn import Session
        from ix.db.models.user import User

        key_hash = _hash_key(raw_key)

        with Session() as session:
            api_key = (
                session.query(cls)
                .filter(cls.key_hash == key_hash, cls.is_revoked == False)
                .first()
            )
            if api_key is None:
                return None

            # Update last_used_at
            api_key.last_used_at = datetime.now(timezone.utc)

            user = (
                session.query(User)
                .filter(User.id == api_key.user_id)
                .first()
            )
            if user is None:
                return None

            # Eagerly load all columns to avoid DetachedInstanceError
            for col in User.__table__.columns:
                getattr(user, col.name)
            session.expunge(user)

        return user

    @classmethod
    def list_for_user(cls, user_id: str) -> List["ApiKey"]:
        """Return all non-revoked keys for a user."""
        from ix.db.conn import Session

        with Session() as session:
            keys = (
                session.query(cls)
                .filter(cls.user_id == user_id, cls.is_revoked == False)
                .order_by(cls.created_at.desc())
                .all()
            )
            for k in keys:
                for col in cls.__table__.columns:
                    getattr(k, col.name)
                session.expunge(k)
            return keys

    @classmethod
    def revoke(cls, key_id: str, user_id: str) -> bool:
        """Soft-revoke a key. Returns True if revoked, False if not found."""
        from ix.db.conn import Session

        with Session() as session:
            api_key = (
                session.query(cls)
                .filter(
                    cls.id == key_id,
                    cls.user_id == user_id,
                    cls.is_revoked == False,
                )
                .first()
            )
            if api_key is None:
                return False
            api_key.is_revoked = True
            return True

    @classmethod
    def count_active(cls, user_id: str) -> int:
        """Count active (non-revoked) keys for a user."""
        from ix.db.conn import Session

        with Session() as session:
            return (
                session.query(cls)
                .filter(cls.user_id == user_id, cls.is_revoked == False)
                .count()
            )
