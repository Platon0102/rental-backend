#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Creating superadmin if not exists..."
python create_superadmin.py

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
