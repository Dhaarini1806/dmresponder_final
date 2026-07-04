#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting Celery worker in background..."
# Run celery with solo pool to minimize memory usage on free tier
celery -A dmresponder worker -l info -P solo --detach

echo "Starting Gunicorn server..."
# Run gunicorn on the port provided by Render
gunicorn dmresponder.wsgi:application --bind 0.0.0.0:$PORT
