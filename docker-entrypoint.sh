#!/bin/bash
set -e

echo "Starting Investment-X Application..."

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
timeout=30
counter=0

while [ $counter -lt $timeout ]; do
    if python -c "from pymongo import MongoClient; import os; client = MongoClient(os.getenv('DB_URL'), serverSelectionTimeoutMS=2000); client.admin.command('ping'); print('MongoDB is ready')" 2>/dev/null; then
        echo "✓ MongoDB is ready!"
        break
    fi
    counter=$((counter+1))
    if [ $counter -eq $timeout ]; then
        echo "Warning: MongoDB is not ready after ${timeout} seconds, starting app anyway..."
        break
    fi
    echo "Waiting for MongoDB... ($counter/$timeout)"
    sleep 1
done

# Run database migrations or setup if needed
# echo "Running database migrations..."
# python -m ix.db.migrations

# Create admin user if needed
if [ -f "create_admin.py" ]; then
    echo "Checking for admin user setup..."
    # Uncomment the line below if you want to auto-create admin user
    # python create_admin.py
fi

# Start the application
echo "Starting Investment-X web application..."
exec python -m ix --host 0.0.0.0 --port ${PORT:-8050}
