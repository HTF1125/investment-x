import sys
import os

# Add the parent directory to the Python path to allow importing ix.db.migrations
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'ix')))

from db.migrations.add_hash_to_insights import run_migration

if __name__ == "__main__":
    run_migration()
