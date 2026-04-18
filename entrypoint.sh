#!/bin/bash
set -e

SERVICE_TYPE="${SERVICE_TYPE:-web}"

echo "=== Starting ApartmentOS ==="
echo "SERVICE_TYPE=${SERVICE_TYPE}"
echo "PORT=${PORT:-8000}"
echo "DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"

case "${SERVICE_TYPE}" in
  web)
    echo "=== Running migrations ==="
    python manage.py migrate --no-input

    echo "=== Starting gunicorn on port ${PORT:-8000} ==="
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
    ;;

  worker)
    echo "=== Starting Celery worker ==="
    exec celery -A config.celery_app worker \
        --loglevel=info \
        --concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
    ;;

  beat)
    echo "=== Starting Celery beat (DatabaseScheduler) ==="
    exec celery -A config.celery_app beat \
        --loglevel=info \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;

  *)
    echo "ERROR: Unknown SERVICE_TYPE='${SERVICE_TYPE}'. Expected one of: web, worker, beat." >&2
    exit 1
    ;;
esac
