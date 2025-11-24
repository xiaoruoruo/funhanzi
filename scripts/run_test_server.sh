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

# Create a default superuser
echo "Creating default superuser (admin/admin)..."
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_PASSWORD=admin
export DJANGO_SUPERUSER_EMAIL=admin@example.com
uv run src/manage.py createsuperuser --noinput || echo "Superuser creation failed (maybe already exists?)"

# Start the Django development server using uv
echo "Starting the Django development server with uv..."
uv run src/manage.py runserver
