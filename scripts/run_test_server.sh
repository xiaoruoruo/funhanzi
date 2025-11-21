#!/bin/bash

# Set the Django settings module to use the local settings
export DJANGO_SETTINGS_MODULE="funhanzi.local_settings"

# Define the path to the database and the test data
DB_FILE="db.sqlite3"
TEST_DATA_DIR="test_data"
TEST_DATA_FILE="$TEST_DATA_DIR/test_data.json"

# Set the python path
export PYTHONPATH=$(pwd)/src

# Create the test_data directory if it doesn't exist
mkdir -p $TEST_DATA_DIR

# Check if the database file exists. If not, create it and load the test data.
if [ ! -f "$DB_FILE" ]; then
    echo "Database file not found. Creating a new one..."
    # Create the database by running migrations
    python src/manage.py migrate

    # Check if the test data file exists
    if [ -f "$TEST_DATA_FILE" ]; then
        echo "Loading test data from $TEST_DATA_FILE..."
        # Load the test data into the sqlite database
        python src/manage.py loaddata $TEST_DATA_FILE
    else
        echo "Test data file not found. Skipping data loading. A new database is created an you can dump data from production."
    fi
else
    echo "Database file found."
fi

# Always run migrations to ensure the database is up to date
echo "Running migrations..."
python src/manage.py migrate

# Start the Django development server using uv
echo "Starting the Django development server with uv..."
uv run python src/manage.py runserver
