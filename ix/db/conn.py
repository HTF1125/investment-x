import os
from bunnet import init_bunnet
from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()

from .models import all_models


client = MongoClient(os.getenv("DATABASE_URL"))
database = client.get_database(os.getenv("DATABASE_NAME", "investmentx"))
init_bunnet(
    database=database,
    document_models=all_models(),
)
print("Database connection initialized and models registered.")


