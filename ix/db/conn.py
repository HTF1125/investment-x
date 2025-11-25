from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from ix.misc import Settings, get_logger
import time
from typing import Optional
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse

logger = get_logger(__name__)

Base = declarative_base()


class Connection:
    """Manages PostgreSQL connection with improved error handling and health checks."""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.Session = None  # scoped_session
        self._is_connected = False

    def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Establishes a connection to PostgreSQL with retry logic.

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retry attempts in seconds

        Returns:
            bool: True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempting to connect to PostgreSQL (attempt {attempt + 1}/{max_retries})..."
                )

                # Get database URL from settings
                settings = Settings()
                # db_url = settings.db_url
                db_url = "postgresql://robertashan1125:kJV4nO4u2eruNiCUo7LwpO6t8ov8JkR7@dpg-d44jfqm3jp1c73ddsae0-a.singapore-postgres.render.com/investmentx_16o7"

                # Convert MongoDB URL format to PostgreSQL if needed
                # If it's already a PostgreSQL URL, use it as is
                if not db_url.startswith("postgresql://") and not db_url.startswith(
                    "postgresql+psycopg2://"
                ):
                    # Assume it's a MongoDB URL and needs conversion
                    # For now, we'll expect a PostgreSQL URL in the format:
                    # postgresql://user:password@host:port/dbname
                    logger.warning("DB_URL should be a PostgreSQL connection string")
                    logger.warning(
                        "Expected format: postgresql://user:password@host:port/dbname"
                    )

                # Ensure we're using psycopg2 driver
                if db_url.startswith("postgresql://"):
                    db_url = db_url.replace(
                        "postgresql://", "postgresql+psycopg2://", 1
                    )

                # Create SQLAlchemy engine with connection pooling
                self.engine = create_engine(
                    db_url,
                    poolclass=QueuePool,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,  # Verify connections before using them
                    pool_recycle=3600,  # Recycle connections after 1 hour
                    echo=False,  # Set to True for SQL query logging
                )

                # Validate connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                # Create session factory
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )

                # Create scoped session for thread-safe session management
                self.Session = scoped_session(self.SessionLocal)

                # Import models to ensure they're registered with Base
                from ix.db import models

                # Create all tables
                Base.metadata.create_all(bind=self.engine)

                # Ensure new columns introduced outside migrations exist
                with self.engine.begin() as conn_check:
                    conn_check.execute(
                        text(
                            "ALTER TABLE IF EXISTS insights ADD COLUMN IF NOT EXISTS pdf_content BYTEA"
                        )
                    )
                    conn_check.execute(
                        text(
                            "ALTER TABLE IF EXISTS timeseries ADD COLUMN IF NOT EXISTS favorite BOOLEAN NOT NULL DEFAULT FALSE"
                        )
                    )
                    conn_check.execute(
                        text(
                            "ALTER TABLE IF EXISTS insights ADD COLUMN IF NOT EXISTS hash_tag VARCHAR"
                        )
                    )

                self._is_connected = True
                logger.info(f"Successfully connected to PostgreSQL: {settings.db_name}")
                return True

            except OperationalError as e:
                logger.error(
                    f"PostgreSQL connection failed (attempt {attempt + 1}): {e}"
                )
            except SQLAlchemyError as e:
                logger.error(
                    f"SQLAlchemy error during connection (attempt {attempt + 1}): {e}"
                )
            except Exception as e:
                logger.exception(
                    f"Unexpected error during PostgreSQL initialization (attempt {attempt + 1}): {e}"
                )

            if attempt < max_retries - 1:
                logger.info(f"Retrying connection in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff

        logger.error(f"Failed to connect to PostgreSQL after {max_retries} attempts")
        return False

    def disconnect(self):
        """Safely closes the PostgreSQL connection."""
        if self.Session is not None:
            try:
                self.Session.remove()  # Remove all scoped sessions
            except Exception as e:
                logger.warning(f"Error removing scoped sessions: {e}")

        if self.engine:
            try:
                self.engine.dispose()
                self._is_connected = False
                logger.info("PostgreSQL connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection: {e}")

    def is_connected(self) -> bool:
        """Check if the database connection is healthy."""
        if not self._is_connected or not self.engine:
            return False

        try:
            # Quick health check
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            self._is_connected = False
            return False

    def get_session(self):
        """Get a database session (scoped session)."""
        if not self.is_connected():
            raise ConnectionError("Database is not connected")
        if self.Session is None:
            raise ConnectionError("Session not initialized. Please connect first.")
        return self.Session()

    @contextmanager
    def session_context(self):
        """Context manager for database session."""
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("Failed to establish database connection")

        if self.Session is None:
            raise ConnectionError("Session not initialized. Please connect first.")

        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self.Session.remove()  # Remove the scoped session from registry

    def __enter__(self):
        """Context manager entry."""
        if not self.connect():
            raise ConnectionError("Failed to establish database connection")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Global database connection instance
conn = Connection()


def get_session():
    """Get a database session (scoped session), ensuring connection is established."""
    if not conn.is_connected():
        if not conn.connect():
            raise ConnectionError("Failed to establish database connection")
    return conn.get_session()


@contextmanager
def Session():
    """Context manager for database session with automatic commit/rollback."""
    if not conn.is_connected():
        if not conn.connect():
            raise ConnectionError("Failed to establish database connection")

    if conn.Session is None:
        raise ConnectionError("Session not initialized. Please connect first.")

    session = conn.Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        conn.Session.remove()  # Remove the scoped session from registry


def ensure_connection():
    """Ensure database connection is established."""
    if not conn.is_connected():
        return conn.connect()
    return True


# Initialize connection on module import
try:
    ensure_connection()
except Exception as e:
    logger.error(f"Failed to initialize database connection: {e}")
    # Don't raise here to allow the application to start and retry later
