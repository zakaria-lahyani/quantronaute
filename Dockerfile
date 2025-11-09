# Quantronaute Trading System - Multi-Broker Docker Image
# This image contains the application code only.
# Configuration is mounted at runtime per broker via volumes.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (config directory will be mounted at runtime)
COPY app/ ./app/

# Copy entrypoint script and fix line endings
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

# Set Python to run in unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default configuration path (can be overridden via environment variable)
ENV CONF_FOLDER_PATH=/app/config

# Use entrypoint to generate .env from environment variables
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command - can be overridden in docker-compose
CMD ["python", "-m", "app.main_multi_symbol"]
