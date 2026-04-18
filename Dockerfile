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

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# NOTE: collectstatic is intentionally NOT run here.
# At build-time R2_*, DJANGO_SECRET_KEY, DATABASE_URL are unavailable, so
# collectstatic would silently fail. It is invoked at runtime in entrypoint.sh
# for the `web` SERVICE_TYPE, where all env vars are injected by Railway.

EXPOSE ${PORT:-8000}

# Run entrypoint (migrations + gunicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
