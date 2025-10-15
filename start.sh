#!/bin/bash

# Set default port if PORT is not set
export PORT=${PORT:-8080}

# Start the application
exec gunicorn ix.web.app:server --bind 0.0.0.0:$PORT --workers 4 --timeout 120
