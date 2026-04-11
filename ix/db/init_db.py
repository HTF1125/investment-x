from ix.db.conn import conn, Base
from ix.db.models import *  # Import all models to ensure they are registered
from ix.common import get_logger

logger = get_logger(__name__)


def init_db():
    logger.info("Initializing database...")
    if not conn.connect():
        logger.error("Failed to connect to database")
        return

    # Create tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=conn.engine, checkfirst=True)

    logger.info("Tables created.")


if __name__ == "__main__":
    init_db()
