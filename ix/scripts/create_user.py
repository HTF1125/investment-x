"""
Utility script to create a user (optionally admin) in the PostgreSQL database.

Usage (from project root):
    python -m ix.scripts.create_user --username someone@example.com --password 'Secret123!' --email someone@example.com --admin
"""

from __future__ import annotations

import argparse
from typing import Optional

from ix.db.conn import Base, conn, ensure_connection, Session
from ix.db.models.user import User


def create_user(
    username: str, password: str, email: Optional[str] = None, admin: bool = False
) -> None:
    ensure_connection()
    # Make sure the User table exists even if not imported during app boot
    Base.metadata.create_all(bind=conn.engine)

    with Session() as session:
        # Check if user exists by username or email
        q = session.query(User).filter(
            (User.username == username) | ((email is not None) & (User.email == email))
        )
        existing = q.first()
        if existing:
            print(
                f"[info] User already exists: {existing.username} (admin={existing.is_admin})"
            )
            return

    # Use model helper which handles hashing & persistence
    user = User.new_user(
        username=username, password=password, email=email, is_admin=admin
    )
    print(f"[ok] Created user '{user.username}' (admin={user.is_admin})")


def main():
    parser = argparse.ArgumentParser(description="Create a user in the database.")
    parser.add_argument("--username", required=True, help="Username (e.g. email)")
    parser.add_argument(
        "--password", required=True, help="Plaintext password to hash and store"
    )
    parser.add_argument(
        "--email", required=False, default=None, help="Email address (optional)"
    )
    parser.add_argument("--admin", action="store_true", help="Create as admin user")
    args = parser.parse_args()

    create_user(
        username=args.username,
        password=args.password,
        email=args.email or args.username,
        admin=args.admin,
    )


if __name__ == "__main__":
    main()
