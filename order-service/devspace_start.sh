#!/bin/bash
set -e

echo "Starting order-service with hot reload..."

# Use Flask development mode for auto-reload
export FLASK_ENV=development
export FLASK_DEBUG=1

# Start the application
python app.py
