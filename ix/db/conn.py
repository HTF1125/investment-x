from pymongo import MongoClient, errors
from bunnet import init_bunnet
from ix.misc import Settings, get_logger
from ix.db import models
import time
from typing import Optional

logger = get_logger(__name__)


class Connection:
    """Manages MongoDB connection with improved error handling and health checks."""

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.database = None
        self._is_connected = False

    def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Establishes a connection to MongoDB with retry logic.

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retry attempts in seconds

        Returns:
            bool: True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempting to connect to MongoDB (attempt {attempt + 1}/{max_retries})..."
                )

                # MongoDB client setup with improved configuration
                self.client = MongoClient(
                    Settings.db_url,
                    serverSelectionTimeoutMS=10000,  # Increased timeout
                    connectTimeoutMS=15000,  # Increased timeout
                    socketTimeoutMS=20000,  # Socket timeout
                    maxPoolSize=100,  # Increased pool size
                    minPoolSize=10,  # Minimum pool size
                    maxIdleTimeMS=30000,  # Max idle time
                    retryWrites=True,
                    retryReads=True,  # Enable retry reads
                    w="majority",  # Write concern
                    journal=True,  # Journal write concern
                )

                # Validate connection
                self.client.admin.command("ping")

                # Select database
                self.database = self.client[Settings.db_name]

                # Initialize Bunnet ODM
                init_bunnet(
                    database=self.database,
                    document_models=models.all(),
                )

                self._is_connected = True
                logger.info(f"Successfully connected to MongoDB: {Settings.db_name}")
                return True

            except errors.ServerSelectionTimeoutError as e:
                logger.error(f"MongoDB connection timeout (attempt {attempt + 1}): {e}")
            except errors.ConnectionFailure as e:
                logger.error(f"MongoDB connection failed (attempt {attempt + 1}): {e}")
            except errors.OperationFailure as e:
                logger.error(
                    f"MongoDB authentication/operation error (attempt {attempt + 1}): {e}"
                )
            except Exception as e:
                logger.exception(
                    f"Unexpected error during MongoDB initialization (attempt {attempt + 1}): {e}"
                )

            if attempt < max_retries - 1:
                logger.info(f"Retrying connection in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff

        logger.error(f"Failed to connect to MongoDB after {max_retries} attempts")
        return False

    def disconnect(self):
        """Safely closes the MongoDB connection."""
        if self.client:
            try:
                self.client.close()
                self._is_connected = False
                logger.info("MongoDB connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

    def is_connected(self) -> bool:
        """Check if the database connection is healthy."""
        if not self._is_connected or not self.client:
            return False

        try:
            # Quick health check
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            self._is_connected = False
            return False

    def get_database(self):
        """Get the database instance."""
        if not self.is_connected():
            raise ConnectionError("Database is not connected")
        return self.database

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


def get_database():
    """Get the database instance, ensuring connection is established."""
    if not conn.is_connected():
        if not conn.connect():
            raise ConnectionError("Failed to establish database connection")
    return conn.get_database()


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
