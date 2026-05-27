#!/bin/sh
set -e

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "Waiting for postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}"; do
  sleep 1
done
echo "Postgres is ready."

echo "Waiting for redis at ${REDIS_HOST}:${REDIS_PORT}..."
until nc -z "${REDIS_HOST}" "${REDIS_PORT}"; do
  sleep 1
done
echo "Redis is ready."

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Applying database migrations..."
  if ! alembic upgrade head; then
    echo "alembic upgrade failed (likely a fresh DB where baseline does not CREATE TABLE)."
    echo "Falling back to SQLAlchemy metadata create_all + stamp head."
    python - <<'PY'
import asyncio
from app.db.session import engine
from app.db.base import Base

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(main())
PY
    alembic stamp head
  fi
fi

exec "$@"
