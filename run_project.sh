#!/bin/bash
echo "Starting SkinSync AI Project..."

# Activate virtual environment
source venv/bin/activate

# Set Flask environment variables
export FLASK_APP=app.py

# Run the Flask application (--debug enables the auto-reloader so code
# changes take effect without restarting the server)
echo "Running Flask..."
flask run --debug
