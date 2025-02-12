#!/bin/bash
set -e  # Exit on error

echo "Starting initialization process..."

# Wait for PostgreSQL to be ready
echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Drop and recreate the database
echo "Dropping and recreating database..."
PGPASSWORD=password psql -h postgres -U user -d postgres -c "DROP DATABASE IF EXISTS messagedb;"
PGPASSWORD=password psql -h postgres -U user -d postgres -c "CREATE DATABASE messagedb;"
echo "Database recreated"

# Run database initialization
echo "Running database initialization..."
python init_db.py

# Verify database setup
echo "Verifying database setup..."
echo "Checking master templates:"
PGPASSWORD=password psql -h postgres -U user -d messagedb -c "SELECT request_type, channel FROM master_templates;"
echo "Checking message requests:"
PGPASSWORD=password psql -h postgres -U user -d messagedb -c "SELECT id, request_type, status FROM message_requests;"

# Start the FastAPI application
echo "Starting publisher service..."
python publisher.py 