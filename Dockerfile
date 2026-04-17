FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY server/requirements/production.txt /app/requirements/production.txt
COPY server/requirements/base.txt /app/requirements/base.txt
RUN pip install --no-cache-dir -r requirements/production.txt

# Copy server code
COPY server/ /app/

# Collect static files
RUN python manage.py collectstatic --no-input || true

EXPOSE ${PORT:-8000}

# Run migrations and start gunicorn
CMD python manage.py migrate --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
