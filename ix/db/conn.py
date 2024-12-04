from pymongo import MongoClient, errors
from bunnet import init_bunnet
from .models import all_models
from ix.misc import Settings


def initialize():
    """
    Initialize Bunnet with MongoDB client and document models.
    """

    try:
        # Initialize MongoDB client with configurations
        client = MongoClient(
            Settings.db_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            maxPoolSize=50,
            retryWrites=True,
        )
        database = client[Settings.db_name]

        # Initialize Bunnet with the database and models
        init_bunnet(
            database=database,
            document_models=all_models(),
        )
        print(f"Successfully initialized Bunnet with MongoDB database: {Settings.db_name}")
        return database  # Optional: return the database object if needed elsewhere

    except errors.ServerSelectionTimeoutError as e:
        print(f"Error: Could not connect to MongoDB server. Timeout reached: {e}")
    except errors.ConnectionFailure as e:
        print(f"Error: Failed to connect to MongoDB: {e}")
    except Exception as e:
        print(f"Unexpected error occurred during Bunnet initialization: {e}")
    return None  # Return None if initialization fails
