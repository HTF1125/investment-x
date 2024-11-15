import os
from pymongo import MongoClient, errors
from dotenv import load_dotenv
from bunnet import init_bunnet
from .models import all_models

# Load environment variables
load_dotenv()

# Fetch environment variables with default values
db_url = os.getenv("DATABASE_URL")
db_name = os.getenv("DATABASE_NAME", "investmentx")

def initialize():
    """
    Initialize Bunnet with MongoDB client and document models.
    """
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")

    try:
        # Initialize MongoDB client with configurations
        client = MongoClient(
            db_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            maxPoolSize=50,
            retryWrites=True
        )
        database = client[db_name]

        # Initialize Bunnet with the database and models
        init_bunnet(
            database=database,
            document_models=all_models(),
        )
        print(f"Successfully initialized Bunnet with MongoDB database: {db_name}")
        return database  # Optional: return the database object if needed elsewhere

    except errors.ServerSelectionTimeoutError as e:
        print(f"Error: Could not connect to MongoDB server. Timeout reached: {e}")
    except errors.ConnectionFailure as e:
        print(f"Error: Failed to connect to MongoDB: {e}")
    except Exception as e:
        print(f"Unexpected error occurred during Bunnet initialization: {e}")

    return None  # Return None if initialization fails
