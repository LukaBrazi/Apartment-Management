#!/bin/bash
set -e

echo "=== Starting ApartmentOS ==="
echo "PORT=${PORT:-8000}"
echo "DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Starting gunicorn on port ${PORT:-8000} ==="
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
