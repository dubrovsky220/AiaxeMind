#!/bin/bash
set -e

echo "Starting AiaxeMind API..."

echo "Waiting for PostgreSQL..."
until PGPASSWORD=${POSTGRES_PASSWORD} psql -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - running migrations"

alembic upgrade head

echo "Migrations completed - starting API server"

exec uvicorn src.api.main:app --host ${API_HOST} --port 8000 --reload
