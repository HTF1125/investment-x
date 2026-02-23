from ix.db.conn import conn, Base
from ix.db.models import *  # Import all models to ensure they are registered
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    logger.info("Initializing database...")
    if not conn.connect():
        logger.error("Failed to connect to database")
        return

    # Create tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=conn.engine)
    logger.info("Tables created.")


if __name__ == "__main__":
    init_db()
