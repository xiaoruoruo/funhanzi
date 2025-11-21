#!/bin/bash

# Set the Django settings module to use the local settings
export DJANGO_SETTINGS_MODULE="funhanzi.local_settings"

# Define the path to the database and the test data
DB_FILE="db.sqlite3"
TEST_DATA_DIR="test_data"
TEST_DATA_FILE="$TEST_DATA_DIR/test_data.json"

# Set the python path
export PYTHONPATH=$(pwd)/src

# Remove the existing database file to ensure a fresh start
echo "Removing existing database file (if any)..."
rm -f $DB_FILE

# Create the database by running migrations
echo "Creating a new database..."
uv run src/manage.py migrate

# Check if the test data file exists and load it
if [ -f "$TEST_DATA_FILE" ]; then
    echo "Loading test data from $TEST_DATA_FILE..."
    uv run src/manage.py loaddata $TEST_DATA_FILE
else
    echo "Test data file not found. Skipping data loading."
fi

# Start the Django development server using uv
echo "Starting the Django development server with uv..."
uv run src/manage.py runserver
