# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install kaleido for plotly image export
RUN pip install kaleido

# Copy the entire project
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p files/Insight files/InsightSource files/Timeseries files/TimeseriesData files/Universe files/User

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh 2>/dev/null || true

# Expose the port the app runs on
EXPOSE 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8050/ || exit 1

# Start the application directly for DigitalOcean
CMD ["python", "-m", "ix", "--host", "0.0.0.0", "--port", "8050"]
