from pymongo import MongoClient, errors
from bunnet import init_bunnet
from ix.misc import Settings, get_logger
from ix.db import models

logger = get_logger(__name__)


"""Establishes a connection to MongoDB and initializes Bunnet."""
try:
    logger.info("Attempting to connect to MongoDB...")

    # MongoDB client setup
    client = MongoClient(
        Settings.db_url,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        maxPoolSize=50,
        retryWrites=True,
    )

    # Validate connection
    client.admin.command("ping")
    logger.info("Successfully connected to MongoDB.")

    # Select database
    database = client[Settings.db_name]

    # Initialize Bunnet ODM
    init_bunnet(
        database=database,
        document_models=models.all(),
    )

    logger.info(f"Successfully initialized Bunnet with database: {Settings.db_name}")
except errors.ServerSelectionTimeoutError as e:
    logger.error(f"MongoDB connection timeout: {e}")
except errors.ConnectionFailure as e:
    logger.error(f"MongoDB connection failed: {e}")
except errors.OperationFailure as e:
    logger.error(f"MongoDB authentication/operation error: {e}")
except Exception as e:
    logger.exception(f"Unexpected error during MongoDB initialization: {e}")
