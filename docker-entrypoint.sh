#!/bin/bash
# Docker entrypoint script for quantronaute trading system
# Dynamically creates /app/.env from ALL environment variables

set -e

echo "================================================================================"
echo "Starting Quantronaute Trading System (Docker)"
echo "================================================================================"

# Create .env file from ALL environment variables
# This works regardless of which symbols or variables are defined
echo "Creating /app/.env from environment variables..."

# Filter environment variables (exclude system/docker vars)
env | grep -v '^PATH=' | \
      grep -v '^HOME=' | \
      grep -v '^HOSTNAME=' | \
      grep -v '^PWD=' | \
      grep -v '^PYTHONUNBUFFERED=' | \
      grep -v '^LANG=' | \
      grep -v '^GPG_KEY=' | \
      grep -v '^PYTHON_' | \
      grep -v '^DEBIAN_' | \
      sort > /app/.env

echo ".env file created with $(wc -l < /app/.env) environment variables"
echo "Configuration loaded from: ${CONF_FOLDER_PATH:-/app/config}"
echo "Trading symbols: ${SYMBOLS:-not specified}"
echo "================================================================================"
echo ""

# Execute the main command (python -m app.main_multi_symbol)
exec "$@"
