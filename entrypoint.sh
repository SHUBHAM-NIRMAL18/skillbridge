#!/bin/sh

set -e

if [ "$DB_HOST" ]; then
    echo "Waiting for database at ${DB_HOST}:${DB_PORT:-5432}..."
    while ! nc -z "${DB_HOST}" "${DB_PORT:-5432}"; do
      sleep 0.5
    done
    echo "Database is ready!"
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

exec "$@"
