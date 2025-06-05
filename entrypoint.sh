#!/bin/bash

# Wait for the database to be ready
until nc -z postgres 5432; do
  echo "Waiting for the database to be ready..."
  sleep 1
done

# Run database migrations
python manage.py migrate

# Start the Django application
exec "$@"
